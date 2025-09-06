#!/usr/bin/env python3
"""
Legal Service Validator - Fail-Fast Service Integration

GUARDRAILS:
- Validates all service integrations before use
- Fails fast and loud on service unavailability  
- Provides detailed error context for debugging
- Never returns partial/corrupted data

PHILOSOPHY:
- Better to crash early than return bad data
- Clear error messages over silent failures
- Validate once, use safely everywhere
"""

import sys
from typing import Any, Dict, Optional

from loguru import logger


class ServiceValidationError(Exception):
    """Raised when service validation fails - FAIL FAST"""
    
    def __init__(self, service_name: str, error: str, context: Dict[str, Any] = None):
        self.service_name = service_name
        self.error = error
        self.context = context or {}
        super().__init__(f"Service '{service_name}' validation failed: {error}")


class LegalServiceValidator:
    """Validates all external service integrations for legal MCP.

    FAIL-FAST PRINCIPLE: If any service is broken, we crash immediately
    rather than return partial or incorrect legal data.
    """
    
    def __init__(self):
        self._entity_service = None
        self._timeline_service = None
        self._validation_cache = {}
    
    def validate_entity_service(self) -> bool:
        """Validate EntityService is working properly.

        FAIL FAST: Raises ServiceValidationError if broken.
        Returns: True if valid (never returns False - crashes instead)
        """
        if 'entity_service' in self._validation_cache:
            return self._validation_cache['entity_service']
            
        try:
            from services import EntityService

            # Test instantiation
            service = EntityService()
            
            # Validate initialization
            if not service.validation_result.get("success", False):
                raise ServiceValidationError(
                    "EntityService",
                    f"Service validation failed: {service.validation_result.get('error', 'Unknown error')}",
                    {"validation_result": service.validation_result}
                )
            
            # Test basic extraction (fail fast if broken)
            test_result = service.extract_email_entities(
                message_id="test_validation_001",
                content="Test entity extraction with John Smith from Apple Inc."
            )
            
            if not test_result.get("success", False):
                raise ServiceValidationError(
                    "EntityService", 
                    f"Entity extraction test failed: {test_result.get('error', 'No error details')}",
                    {"test_result": test_result}
                )
            
            # Cache successful validation and service instance
            self._entity_service = service
            self._validation_cache['entity_service'] = True
            logger.info("✅ EntityService validation passed")
            return True
            
        except ImportError as e:
            raise ServiceValidationError(
                "EntityService",
                f"Import failed: {e}",
                {"import_error": str(e), "sys_path": sys.path[:3]}
            )
        except Exception as e:
            raise ServiceValidationError(
                "EntityService",
                f"Unexpected error during validation: {e}",
                {"exception_type": type(e).__name__, "exception_str": str(e)}
            )
    
    def validate_timeline_service(self) -> bool:
        """Validate TimelineService is working properly.

        FAIL FAST: Raises ServiceValidationError if broken.
        Returns: True if valid (never returns False - crashes instead)
        """
        if 'timeline_service' in self._validation_cache:
            return self._validation_cache['timeline_service']
            
        try:
            from lib import TimelineService

            # Test instantiation
            service = TimelineService()
            
            # Test basic timeline view (fail fast if broken)
            test_result = service.get_timeline_view(limit=1)
            
            if not isinstance(test_result, dict):
                raise ServiceValidationError(
                    "TimelineService",
                    f"get_timeline_view returned invalid type: {type(test_result)}",
                    {"returned_value": str(test_result)[:200]}
                )
            
            # Cache successful validation and service instance  
            self._timeline_service = service
            self._validation_cache['timeline_service'] = True
            logger.info("✅ TimelineService validation passed")
            return True
            
        except ImportError as e:
            raise ServiceValidationError(
                "TimelineService",
                f"Import failed: {e}",
                {"import_error": str(e), "sys_path": sys.path[:3]}
            )
        except Exception as e:
            raise ServiceValidationError(
                "TimelineService", 
                f"Unexpected error during validation: {e}",
                {"exception_type": type(e).__name__, "exception_str": str(e)}
            )
    
    def get_validated_entity_service(self) -> Any:
        """Get EntityService instance after validation.

        FAIL FAST: Will crash if service not validated or broken.
        """
        if not self.validate_entity_service():
            raise ServiceValidationError("EntityService", "Validation failed but no exception raised")
            
        if self._entity_service is None:
            raise ServiceValidationError("EntityService", "Service validated but instance is None")
            
        return self._entity_service
    
    def get_validated_timeline_service(self) -> Any:
        """Get TimelineService instance after validation.

        FAIL FAST: Will crash if service not validated or broken.
        """
        if not self.validate_timeline_service():
            raise ServiceValidationError("TimelineService", "Validation failed but no exception raised")
            
        if self._timeline_service is None:
            raise ServiceValidationError("TimelineService", "Service validated but instance is None")
            
        return self._timeline_service
    
    def validate_all_services(self) -> Dict[str, bool]:
        """Validate all services required for legal MCP.

        FAIL FAST: Will crash on first service failure.
        Returns: Dict of validation results (only if ALL pass)
        """
        results = {}
        
        try:
            results['entity_service'] = self.validate_entity_service()
            results['timeline_service'] = self.validate_timeline_service()
            
            logger.info(f"✅ All legal services validated: {list(results.keys())}")
            return results
            
        except ServiceValidationError:
            logger.error("❌ Legal service validation failed - failing fast")
            raise


# Singleton validator instance
_validator: Optional[LegalServiceValidator] = None


def get_legal_service_validator() -> LegalServiceValidator:
    """
    Get singleton service validator instance.
    """
    global _validator
    if _validator is None:
        _validator = LegalServiceValidator()
    return _validator


def validate_legal_services_or_crash() -> Dict[str, bool]:
    """Validate all legal services OR crash the process.

    This function implements FAIL-FAST philosophy:
    - Either all services work perfectly
    - Or we crash with detailed error information
    - Never returns partial success
    """
    validator = get_legal_service_validator()
    return validator.validate_all_services()


if __name__ == "__main__":
    # Test the validator
    try:
        results = validate_legal_services_or_crash()
        print("✅ All services validated successfully:")
        for service, status in results.items():
            print(f"  - {service}: {'✅' if status else '❌'}")
    except ServiceValidationError as e:
        print(f"❌ Validation failed: {e}")
        if e.context:
            print(f"Context: {e.context}")
        sys.exit(1)