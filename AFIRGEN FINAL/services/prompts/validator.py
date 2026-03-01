"""
Prompt validation utilities.
Validates prompt templates and formatted prompts.
"""

import re
from typing import List, Set


class PromptValidationError(Exception):
    """Exception raised for prompt validation errors."""
    pass


class PromptValidator:
    """Validates prompt templates and formatted prompts."""
    
    MAX_PROMPT_LENGTH = 100000  # Claude's context window limit
    
    @staticmethod
    def validate_template(
        template: str,
        required_placeholders: List[str]
    ) -> bool:
        """
        Validate that template contains all required placeholders.
        
        Args:
            template: Prompt template string
            required_placeholders: List of required placeholder names
        
        Returns:
            True if valid
        
        Raises:
            PromptValidationError: If validation fails
        """
        if not template or not template.strip():
            raise PromptValidationError("Template cannot be empty")
        
        # Extract placeholders from template
        placeholders = set(re.findall(r'\{(\w+)\}', template))
        
        # Check for missing placeholders
        missing = set(required_placeholders) - placeholders
        if missing:
            raise PromptValidationError(
                f"Template missing required placeholders: {', '.join(missing)}"
            )
        
        # Check for undefined placeholders
        undefined = placeholders - set(required_placeholders)
        if undefined:
            raise PromptValidationError(
                f"Template contains undefined placeholders: {', '.join(undefined)}"
            )
        
        return True
    
    @staticmethod
    def validate_formatted_prompt(prompt: str, max_length: int = None) -> bool:
        """
        Validate formatted prompt.
        
        Args:
            prompt: Formatted prompt string
            max_length: Maximum allowed length (defaults to MAX_PROMPT_LENGTH)
        
        Returns:
            True if valid
        
        Raises:
            PromptValidationError: If validation fails
        """
        if not prompt or not prompt.strip():
            raise PromptValidationError("Prompt cannot be empty")
        
        max_len = max_length or PromptValidator.MAX_PROMPT_LENGTH
        if len(prompt) > max_len:
            raise PromptValidationError(
                f"Prompt exceeds maximum length: {len(prompt)} > {max_len}"
            )
        
        # Check for unformatted placeholders
        unformatted = re.findall(r'\{(\w+)\}', prompt)
        if unformatted:
            raise PromptValidationError(
                f"Prompt contains unformatted placeholders: {', '.join(unformatted)}"
            )
        
        return True
    
    @staticmethod
    def validate_parameters(
        temperature: float,
        max_tokens: int
    ) -> bool:
        """
        Validate prompt parameters.
        
        Args:
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            True if valid
        
        Raises:
            PromptValidationError: If validation fails
        """
        if not 0.0 <= temperature <= 1.0:
            raise PromptValidationError(
                f"Temperature must be between 0.0 and 1.0, got {temperature}"
            )
        
        if not 1 <= max_tokens <= 4096:
            raise PromptValidationError(
                f"Max tokens must be between 1 and 4096, got {max_tokens}"
            )
        
        return True
    
    @staticmethod
    def extract_placeholders(template: str) -> Set[str]:
        """
        Extract all placeholders from template.
        
        Args:
            template: Prompt template string
        
        Returns:
            Set of placeholder names
        """
        return set(re.findall(r'\{(\w+)\}', template))
