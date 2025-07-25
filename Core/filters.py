from rest_framework.filters import BaseFilterBackend   #type: ignore
from django.db.models import (   #type: ignore
    Q, CharField, TextField, EmailField, 
    IntegerField, FloatField, BooleanField, 
    DateField, DateTimeField
) 
from django.db.models.fields.related import ForeignKey   #type: ignore

MAX_DEPTH = 3  # Prevent infinite loops and performance issues

def get_searchable_fields(model, prefix='', depth=0):
    if depth > MAX_DEPTH:
        return []

    fields = []
    for field in model._meta.get_fields():
        if hasattr(field, 'get_internal_type') and isinstance(field, (CharField, TextField, EmailField, IntegerField, FloatField, BooleanField, DateField, DateTimeField)):
            fields.append(f"{prefix}{field.name}")
        elif isinstance(field, ForeignKey):
            rel_model = field.related_model
            rel_prefix = f"{prefix}{field.name}__"
            fields.extend(get_searchable_fields(rel_model, rel_prefix, depth + 1))

    return fields

class ExtendedMultiKeywordSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search_query = request.query_params.get('search', None)
        if not search_query:
            return queryset

        model = queryset.model
        keywords = search_query.split()

        # Define field types to include
        field_types = (
            CharField, TextField, EmailField,
            IntegerField, FloatField,
            BooleanField,
            DateField, DateTimeField
        )

        # Level 1 Search
        # # Get local fields
        # fields = [
        #     field.name for field in model._meta.get_fields()
        #     if hasattr(field, 'get_internal_type') and isinstance(field, field_types)
        # ]

        # Level 2 Search
        # # Add related model fields (ForeignKey)
        # for field in model._meta.get_fields():
        #     if isinstance(field, ForeignKey):
        #         rel_model = field.related_model
        #         rel_fields = [
        #             f.name for f in rel_model._meta.get_fields()
        #             if hasattr(f, 'get_internal_type') and isinstance(f, field_types)
        #         ]
        #         fields.extend([f"{field.name}__{rel_f}" for rel_f in rel_fields])

        # Multi-Level Search
        fields = get_searchable_fields(model)

        # Build query
        for keyword in keywords:
            query = Q()
            for field in fields:
                query |= Q(**{f"{field}__icontains": keyword})
            queryset = queryset.filter(query)

        return queryset
