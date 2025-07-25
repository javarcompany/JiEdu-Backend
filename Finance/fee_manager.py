from django.utils import timezone #type: ignore
from typing import Dict, Tuple, List
from decimal import Decimal, ROUND_DOWN


from .models import Receipt, Transaction, FeeParticular, Account, FeeStatus, Invoice
from Students.models import Student, Allocate_Student

class FeeManager:
    def __init__(self, student_regno, term_id):
        self.student = Student.objects.get(regno=student_regno)
        self.term = term_id
        self.module = Allocate_Student.objects.get(studentno = self.student).module

    def get_paid_records(self) -> Dict[FeeParticular, int]:
        """
        Fetches total amount paid per votehead (Account) for this student in the current term.
        Returns a dict of {Votehead: total_paid}.
        """
        paid_records: Dict[FeeParticular, Decimal] = {}

        receipts = Receipt.objects.filter(student__regno = self.student, term__id = self.term)

        transactions = Transaction.objects.filter(receipt__in=receipts)
        for tx in transactions:
            account = tx.account
            paid_records[account] = paid_records.get(account, 0) + tx.amount

        return paid_records

    def get_structure(self) -> Dict[FeeParticular, int]:
        """
        Returns a dictionary {Account: amount} representing the expected fee structure
        for the student's course, module, and term.
        """
        structure = {}
        particulars = FeeParticular.objects.filter(
            course = self.student.course, 
            module = self.module, 
            term__id = self.term
        )

        for item in particulars:
            structure[item] = structure.get(item, 0) + item.amount

        return structure
    
    def get_invoice_items(self, invoice) -> Dict[FeeParticular, Decimal]:
        """
        Returns a dict {FeeParticular: amount} for the invoice issued to the student for the current term.
        """
        structure = {}

        if not invoice:
            return {}

        for item in invoice.narration.all():
            structure[item] = structure.get(item, Decimal("0.00")) + item.amount

        return structure

    def get_priorities(self) -> Dict[Account, int]:
        """
        Returns a dictionary {Account: priority_percentage} for all defined priorities.
        """
        priorities = {}

        accounts = Account.objects.select_related("priority").all()

        for account in accounts:
            if account.priority:
                priorities[account] = account.priority.rank

        return priorities

    def get_particular_balance(self, structure: Dict[FeeParticular, int], paid: Dict[FeeParticular, int]) -> Dict[FeeParticular, int]:
        """
        Compares the fee structure with paid records and returns a dictionary of remaining balances.

        Parameters:
            structure: dict of {Account: expected_amount}
            paid: dict of {Account: paid_amount}

        Returns:
            dict of {Account: remaining_amount}
        """
        remaining = {}

        for account, expected_amount in structure.items():
            paid_amount = paid.get(account, 0)
            if paid_amount < expected_amount:
                remaining[account] = expected_amount - paid_amount

        return remaining
 
    def filter_priorities(self, unpaid: Dict[FeeParticular, int], priorities: Dict[Account, int]) -> Dict[FeeParticular, int]:
        """
        Filters and sorts priority voteheads based on unpaid voteheads.

        Parameters:
            unpaid: dict of {Votehead: remaining_amount}
            priorities: dict of {"Votehead Name": percentage}

        Returns:
            Sorted dict of {Votehead: percentage} by descending priority
        """
        filtered = {
            account: priorities[account.account]
            for account in unpaid if account.account in priorities
        }

        return dict(sorted(filtered.items(), key=lambda item: item[1], reverse=True))

    def allocate_payment( self, amount: Decimal, distribution: Dict[FeeParticular, Tuple[Decimal, int]]) -> Dict[FeeParticular, Decimal]:
        """
        Allocate payment based on account priorities and remaining balances.

        Parameters:
            amount: total amount available to allocate (Decimal)
            distribution: {Account: (balance_due, priority_percent)}

        Returns:
            Dict of {Account: allocated_amount}
        """

        # Step 1: Sort Accounts by priority ascending
        sorted_distribution = dict(
            sorted(distribution.items(), key=lambda item: item[1][1], reverse=False)
        )

        total_balance = sum(balance for balance, _ in sorted_distribution.values())
        particular_balance = {account: Decimal("0.00") for account in sorted_distribution}

        # Step 2: Full payment case
        if amount >= total_balance:
            for account, (balance_due, _) in sorted_distribution.items():
                particular_balance[account] = balance_due
            return particular_balance

        # Step 3: Partial payment case - handle 100% priority logic
        remaining_distribution = {}
        for account, (balance_due, priority) in sorted_distribution.items():
            if amount <= Decimal("0.00"):
                break

            if priority == 100:
                # Full priority
                if amount >= balance_due:
                    particular_balance[account] = balance_due
                    amount -= balance_due
                else:
                    particular_balance[account] = amount
                    amount = Decimal("0.00")
            else:
                remaining_distribution[account] = (balance_due, priority)
        
        if amount <= Decimal("0.00"):
            return particular_balance

        # Step 4: Handle priorities less than 100%
        # A) Total balance of remaining voteheads
        remaining_total_balance = sum(balance for balance, _ in remaining_distribution.values())

        if remaining_total_balance <= 0:
            return particular_balance

        # B) Loop and distribute based on priority logic
        while amount > Decimal("0.00"):
            distributed = False

            for account, (balance_due, priority) in remaining_distribution.items():
                already_allocated = particular_balance[account]
                remaining = balance_due - already_allocated
                if remaining <= Decimal("0.00"):
                    continue

                # Ratio-based allocation
                ratio_based = ((balance_due / remaining_total_balance) * amount).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

                # Priority-based allocation
                priority_based = ((Decimal(priority) / Decimal("100.00")) * balance_due).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

                # Choose the smaller of the two
                allocation = min(ratio_based, priority_based, remaining, amount)

                if allocation <= Decimal("0.00"):
                    continue

                particular_balance[account] += allocation
                amount -= allocation
                distributed = True

                if amount <= Decimal("0.00"):
                    break

            if not distributed:
                break  # No more allocations possible, avoid infinite loop

        return particular_balance
    
    def apply_payment(self, receipt: Receipt, distributed: Dict[FeeParticular, Decimal]) -> None:
        """
        Applies and records the payment allocations to the database.

        Parameters:
            receipt: The Reciept object to associate the transactions with.
            distributed: {Account: allocated_amount}
        """
        total = sum(distributed.values())
        running_balance = total

        for account, amount in distributed.items():
            if amount <= Decimal("0.00"):
                continue

            running_balance -= amount

            Transaction.objects.create(
                receipt = receipt,
                amount = amount,
                running_balance = running_balance,
                account = account,
            )

    def update_status(self, receipt: str, amount_paid: Decimal) -> None:
        """
        Updates the student's fee clearance status based on arrears.

        Parameters:
            arrears (decimal): The remaining balance after the payment allocation.
        """
        arrears = Decimal("0.00")

        # Get current status
        latest_status = FeeStatus.objects.filter(student=self.student).order_by('-created_at').first()        
        if latest_status:
            previous_arrears = latest_status.arrears or Decimal("0.00")
            arrears = previous_arrears + amount_paid
        else:
            arrears = amount_paid

        if arrears > 0:
            status = "Overpaid"
        elif arrears < 0:
            status = "Not-Cleared"
        else:
            status = "Cleared"

        # Update fee status record
        FeeStatus.objects.create(
            student = self.student,
            term_id = self.term,
            module = self.module,
            status = status,
            arrears = arrears,
            purpose = receipt,
            created_at = timezone.now()
        )

