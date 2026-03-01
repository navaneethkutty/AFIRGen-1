"""
Unit tests for prompt templates and validation.
"""

import pytest

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.prompts.templates import PromptTemplates, PromptConfig
from services.prompts.validator import PromptValidator, PromptValidationError


class TestPromptTemplates:
    """Test suite for PromptTemplates."""
    
    def test_legal_narrative_config(self):
        """Test legal narrative prompt configuration."""
        config = PromptTemplates.LEGAL_NARRATIVE
        assert isinstance(config, PromptConfig)
        assert config.temperature == 0.3
        assert config.max_tokens == 500
        assert 'complaint_text' in config.required_placeholders
    
    def test_metadata_extraction_config(self):
        """Test metadata extraction prompt configuration."""
        config = PromptTemplates.METADATA_EXTRACTION
        assert config.temperature == 0.1
        assert config.max_tokens == 300
        assert 'narrative' in config.required_placeholders
    
    def test_fir_generation_config(self):
        """Test FIR generation prompt configuration."""
        config = PromptTemplates.FIR_GENERATION
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert 'narrative' in config.required_placeholders
        assert 'ipc_sections' in config.required_placeholders
    
    def test_format_legal_narrative_prompt(self):
        """Test formatting legal narrative prompt."""
        result = PromptTemplates.format_legal_narrative_prompt(
            complaint_text="Someone stole my phone"
        )
        
        assert 'prompt' in result
        assert 'temperature' in result
        assert 'max_tokens' in result
        assert "Someone stole my phone" in result['prompt']
        assert result['temperature'] == 0.3
        assert result['max_tokens'] == 500
    
    def test_format_metadata_extraction_prompt(self):
        """Test formatting metadata extraction prompt."""
        result = PromptTemplates.format_metadata_extraction_prompt(
            narrative="Formal legal narrative text"
        )
        
        assert 'prompt' in result
        assert "Formal legal narrative text" in result['prompt']
        assert result['temperature'] == 0.1
        assert result['max_tokens'] == 300
    
    def test_format_fir_generation_prompt(self):
        """Test formatting FIR generation prompt."""
        result = PromptTemplates.format_fir_generation_prompt(
            narrative="Formal narrative",
            incident_type="theft",
            incident_date="2024-01-15",
            location="Mumbai",
            complainant_name="John Doe",
            accused_name="Jane Smith",
            description="Phone theft",
            ipc_sections="Section 379: Theft"
        )
        
        assert 'prompt' in result
        assert "theft" in result['prompt']
        assert "Mumbai" in result['prompt']
        assert "John Doe" in result['prompt']
        assert "Section 379" in result['prompt']
        assert result['temperature'] == 0.5
        assert result['max_tokens'] == 2048
    
    def test_format_fir_generation_prompt_with_nulls(self):
        """Test FIR prompt formatting with null values."""
        result = PromptTemplates.format_fir_generation_prompt(
            narrative="Narrative",
            incident_type="assault",
            incident_date=None,
            location="Delhi",
            complainant_name="Test User",
            accused_name=None,
            description="Assault incident",
            ipc_sections="Section 323"
        )
        
        assert "Not specified" in result['prompt']  # For null date
        assert "Unknown" in result['prompt']  # For null accused


class TestPromptValidator:
    """Test suite for PromptValidator."""
    
    def test_validate_template_success(self):
        """Test successful template validation."""
        template = "Hello {name}, your {item} is ready."
        required = ['name', 'item']
        
        assert PromptValidator.validate_template(template, required) is True
    
    def test_validate_template_missing_placeholder(self):
        """Test template validation with missing placeholder."""
        template = "Hello {name}"
        required = ['name', 'item']
        
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_template(template, required)
        
        assert "missing required placeholders" in str(exc_info.value).lower()
    
    def test_validate_template_undefined_placeholder(self):
        """Test template validation with undefined placeholder."""
        template = "Hello {name}, {extra}"
        required = ['name']
        
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_template(template, required)
        
        assert "undefined placeholders" in str(exc_info.value).lower()
    
    def test_validate_template_empty(self):
        """Test template validation with empty template."""
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_template("", ['name'])
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_validate_formatted_prompt_success(self):
        """Test successful formatted prompt validation."""
        prompt = "Hello John, your order is ready."
        assert PromptValidator.validate_formatted_prompt(prompt) is True
    
    def test_validate_formatted_prompt_empty(self):
        """Test formatted prompt validation with empty prompt."""
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_formatted_prompt("")
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_validate_formatted_prompt_too_long(self):
        """Test formatted prompt validation with excessive length."""
        long_prompt = "x" * 200000
        
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_formatted_prompt(long_prompt)
        
        assert "exceeds maximum length" in str(exc_info.value).lower()
    
    def test_validate_formatted_prompt_unformatted_placeholder(self):
        """Test formatted prompt with unformatted placeholder."""
        prompt = "Hello {name}, your order is ready."
        
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_formatted_prompt(prompt)
        
        assert "unformatted placeholders" in str(exc_info.value).lower()
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation."""
        assert PromptValidator.validate_parameters(0.5, 1000) is True
    
    def test_validate_parameters_invalid_temperature(self):
        """Test parameter validation with invalid temperature."""
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_parameters(1.5, 1000)
        
        assert "temperature" in str(exc_info.value).lower()
    
    def test_validate_parameters_invalid_max_tokens(self):
        """Test parameter validation with invalid max_tokens."""
        with pytest.raises(PromptValidationError) as exc_info:
            PromptValidator.validate_parameters(0.5, 5000)
        
        assert "max tokens" in str(exc_info.value).lower()
    
    def test_extract_placeholders(self):
        """Test placeholder extraction."""
        template = "Hello {name}, your {item} is {status}."
        placeholders = PromptValidator.extract_placeholders(template)
        
        assert placeholders == {'name', 'item', 'status'}
    
    def test_extract_placeholders_none(self):
        """Test placeholder extraction with no placeholders."""
        template = "Hello world"
        placeholders = PromptValidator.extract_placeholders(template)
        
        assert placeholders == set()
