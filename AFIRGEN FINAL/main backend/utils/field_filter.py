"""
Field Filtering Utility for API Response Optimization.

This module provides utilities for filtering response fields:
- Field validation against allowed fields
- Field filtering for dictionaries and lists
- Support for nested field filtering

Requirements: 3.4
"""

from typing import Any, Dict, List, Optional, Set, Union
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class FieldFilter:
    """
    Handler for field filtering operations.
    
    Provides validation and filtering of response fields to reduce payload size.
    """
    
    @staticmethod
    def validate_fields(fields: List[str], allowed: List[str]) -> bool:
        """
        Validate that requested fields are in the allowed list.
        
        Args:
            fields: List of requested field names
            allowed: List of allowed field names
            
        Returns:
            True if all requested fields are allowed, False otherwise
            
        Requirements: 3.4
        """
        if not fields:
            return True
        
        allowed_set = set(allowed)
        requested_set = set(fields)
        
        # Check if all requested fields are in allowed set
        invalid_fields = requested_set - allowed_set
        
        if invalid_fields:
            logger.warning("Invalid fields requested", invalid_fields=list(invalid_fields), allowed_fields=allowed)
            return False
        
        return True
    
    @staticmethod
    def filter_fields(data: Union[Dict[str, Any], List[Dict[str, Any]]], 
                     fields: Optional[List[str]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Filter dictionary or list of dictionaries to include only specified fields.
        
        Args:
            data: Dictionary or list of dictionaries to filter
            fields: List of field names to include (None means include all)
            
        Returns:
            Filtered data with only requested fields
            
        Requirements: 3.4
        """
        if fields is None or len(fields) == 0:
            # No filtering requested, return all fields
            return data
        
        fields_set = set(fields)
        
        if isinstance(data, dict):
            # Filter single dictionary
            return FieldFilter._filter_dict(data, fields_set)
        elif isinstance(data, list):
            # Filter list of dictionaries
            return [FieldFilter._filter_dict(item, fields_set) 
                   for item in data if isinstance(item, dict)]
        else:
            # Unsupported type, return as-is
            logger.warning("Unsupported data type for filtering", data_type=str(type(data)))
            return data
    
    @staticmethod
    def _filter_dict(data: Dict[str, Any], fields: Set[str]) -> Dict[str, Any]:
        """
        Filter a single dictionary to include only specified fields.
        
        Args:
            data: Dictionary to filter
            fields: Set of field names to include
            
        Returns:
            Filtered dictionary
        """
        return {key: value for key, value in data.items() if key in fields}
    
    @staticmethod
    def get_allowed_fields(model_class: Any) -> List[str]:
        """
        Get list of allowed fields from a model class.
        
        Args:
            model_class: Model class (Pydantic, dataclass, or dict)
            
        Returns:
            List of allowed field names
            
        Requirements: 3.4
        """
        # Try Pydantic model
        if hasattr(model_class, '__fields__'):
            return list(model_class.__fields__.keys())
        
        # Try dataclass
        if hasattr(model_class, '__dataclass_fields__'):
            return list(model_class.__dataclass_fields__.keys())
        
        # Try dict with keys
        if isinstance(model_class, dict):
            return list(model_class.keys())
        
        # Fallback: return empty list
        logger.warning("Could not extract fields from model", model_type=str(type(model_class)))
        return []
    
    @staticmethod
    def parse_fields_param(fields_param: Optional[str]) -> Optional[List[str]]:
        """
        Parse fields parameter from query string.
        
        Supports comma-separated field names.
        
        Args:
            fields_param: Comma-separated field names (e.g., "id,name,email")
            
        Returns:
            List of field names or None if no fields specified
            
        Requirements: 3.4
        """
        if not fields_param:
            return None
        
        # Split by comma and strip whitespace
        fields = [field.strip() for field in fields_param.split(',')]
        
        # Filter out empty strings
        fields = [field for field in fields if field]
        
        if not fields:
            return None
        
        logger.debug("Parsed fields", fields=fields)
        return fields
    
    @staticmethod
    def filter_response(data: Any, 
                       fields: Optional[List[str]], 
                       allowed_fields: Optional[List[str]] = None) -> Any:
        """
        Complete field filtering workflow with validation.
        
        Args:
            data: Data to filter (dict or list of dicts)
            fields: Requested fields
            allowed_fields: Allowed fields (None means no validation)
            
        Returns:
            Filtered data
            
        Raises:
            ValueError: If requested fields are not allowed
            
        Requirements: 3.4
        """
        # If no fields requested, return all data
        if not fields:
            return data
        
        # Validate fields if allowed_fields is provided
        if allowed_fields is not None:
            if not FieldFilter.validate_fields(fields, allowed_fields):
                invalid = set(fields) - set(allowed_fields)
                raise ValueError(f"Invalid fields requested: {invalid}")
        
        # Filter data
        return FieldFilter.filter_fields(data, fields)
