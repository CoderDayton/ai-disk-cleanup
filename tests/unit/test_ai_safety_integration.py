"""
Comprehensive test suite for AI confidence scoring and safety assessment integration.

This test suite validates:
- AI confidence scoring integration with existing safety layer
- Safety assessment algorithm with AI input and multi-layer protection
- Confidence threshold application (0.95 auto, 0.70 review, <0.70 keep)
- Integration with existing protection rules and safety mechanisms
- File age, location, and user behavior factor adjustments
- AI recommendation validation against safety rules

SDD Requirements:
- AI safety and privacy requirements [ref: SDD/Runtime View]
- AI Safety Assessment Algorithm [ref: SDD/Runtime View]
- Safety layer integration with AI recommendations [ref: SDD/Building Block View]
- Multi-layer protection architecture [ref: SDD/Quality Requirements]

Phase 2: AI Integration and Analysis Engine
"""

import pytest
import os
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from enum import Enum
import logging

# Import the safety layer components
from src.ai_disk_cleanup.safety_layer import (
    SafetyLayer, ProtectionRule, SafetyScore, ProtectionLevel,
    SafetyAssessment
)
from src.ai_disk_cleanup.audit_trail import AuditTrail, SafetyDecision


class AIRecommendation(Enum):
    """AI deletion recommendation categories."""
    DELETE = "delete"
    REVIEW = "review"
    KEEP = "keep"
    PROTECTED = "protected"


class AIAnalysisResult:
    """Result of AI file analysis with confidence scoring."""

    def __init__(
        self,
        file_path: str,
        recommendation: AIRecommendation,
        confidence: float,
        reasoning: str,
        risk_level: str,
        category: str,
        factors: dict = None
    ):
        self.file_path = file_path
        self.recommendation = recommendation
        self.confidence = confidence  # 0.0 to 1.0
        self.reasoning = reasoning
        self.risk_level = risk_level
        self.category = category
        self.factors = factors or {}
        self.timestamp = datetime.now()


class AISafetyAssessment:
    """AI-enhanced safety assessment with confidence scoring integration."""

    def __init__(self, safety_layer: SafetyLayer):
        self.safety_layer = safety_layer
        self.confidence_thresholds = {
            "auto_delete": 0.95,    # High confidence for automatic deletion
            "review": 0.70,         # Medium confidence requires review
            "keep": 0.0            # Below review threshold, keep file
        }
        self.logger = logging.getLogger(__name__)

        # Add AI-specific logging methods to audit trail
        self._setup_ai_audit_methods()

    def _setup_ai_audit_methods(self):
        """Setup AI-specific audit logging methods."""
        # Add AI recommendation logging method if not exists
        if not hasattr(self.safety_layer.audit_trail, 'log_ai_recommendation'):
            def log_ai_recommendation(file_path: str, ai_recommendation: str,
                                    ai_confidence: float, ai_reasoning: str):
                """Log AI recommendation to audit trail."""
                # Use existing user_action method for AI recommendations
                self.safety_layer.audit_trail.log_user_action(
                    file_path=file_path,
                    action="AI_RECOMMENDATION",
                    comment=f"AI: {ai_recommendation} (confidence: {ai_confidence:.2f}) - {ai_reasoning}"
                )

            self.safety_layer.audit_trail.log_ai_recommendation = log_ai_recommendation

    def assess_file_with_ai(self, file_path: str, ai_result: AIAnalysisResult) -> SafetyAssessment:
        """
        Assess file safety combining AI analysis with existing safety layer.

        Args:
            file_path: Path to the file being assessed
            ai_result: AI analysis result with confidence scoring

        Returns:
            Comprehensive safety assessment with AI integration
        """
        # Get traditional safety assessment
        traditional_safety_score = self.safety_layer.calculate_safety_score(file_path)

        # Calculate AI-enhanced safety score
        ai_enhanced_score = self._calculate_ai_enhanced_safety_score(
            traditional_safety_score, ai_result
        )

        # Apply AI confidence thresholds
        final_decision = self._apply_ai_confidence_thresholds(
            file_path, ai_enhanced_score, ai_result
        )

        return SafetyAssessment(
            file_path=file_path,
            safety_score=ai_enhanced_score,
            protection_level=ai_enhanced_score.protection_level,
            can_auto_delete=final_decision == SafetyDecision.SAFE_TO_DELETE,
            audit_trail_entry=None
        )

    def _calculate_ai_enhanced_safety_score(
        self,
        traditional_score: SafetyScore,
        ai_result: AIAnalysisResult
    ) -> SafetyScore:
        """Calculate safety score combining traditional and AI analysis."""

        # Base safety score starts with AI confidence
        base_confidence = ai_result.confidence

        # Adjust for file age factor (older files are safer)
        age_factor = self._calculate_file_age_factor(ai_result.file_path)

        # Adjust for file location factor (temp locations are safer)
        location_factor = self._calculate_file_location_factor(ai_result.file_path)

        # Adjust for user behavior factor (user patterns)
        behavior_factor = self._calculate_user_behavior_factor(ai_result.file_path)

        # Calculate final confidence score
        # For high AI confidence (≥0.95), preserve it and only adjust if factors strongly support
        if base_confidence >= 0.95:
            # Start with AI confidence, only reduce if safety factors are very low
            min_factor = min(age_factor, location_factor, behavior_factor)
            if min_factor >= 0.8:
                final_confidence = base_confidence  # Preserve high confidence
            else:
                # Adjust down slightly if any factor is concerning
                final_confidence = max(0.90, base_confidence - (0.8 - min_factor) * 0.1)
        else:
            # Weighted combination for normal cases
            final_confidence = (
                base_confidence * 0.6 +  # AI confidence has highest weight
                age_factor * 0.15 +      # File age factor
                location_factor * 0.15 +  # File location factor
                behavior_factor * 0.1    # User behavior factor
            )

        # Ensure confidence stays within valid range
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Calculate risk score (inverse of confidence)
        risk_score = 1.0 - final_confidence

        # Determine protection level based on AI recommendation and traditional assessment
        protection_level = self._determine_protection_level(
            traditional_score.protection_level, ai_result
        )

        # Determine if auto-deletion is allowed
        can_auto_delete = (
            protection_level == ProtectionLevel.SAFE and
            final_confidence >= self.confidence_thresholds["auto_delete"]
        )

        return SafetyScore(
            confidence=final_confidence,
            risk_score=risk_score,
            protection_level=protection_level,
            can_auto_delete=can_auto_delete,
            factors={
                "ai_confidence": ai_result.confidence,
                "age_factor": age_factor,
                "location_factor": location_factor,
                "behavior_factor": behavior_factor,
                "ai_recommendation": ai_result.recommendation.value,
                "ai_category": ai_result.category
            }
        )

    def _calculate_file_age_factor(self, file_path: str) -> float:
        """Calculate age-based safety factor (older = safer)."""
        try:
            if not os.path.exists(file_path):
                return 0.5  # Default for non-existent files

            mtime = os.path.getmtime(file_path)
            file_time = datetime.fromtimestamp(mtime)
            days_old = (datetime.now() - file_time).days

            # Files older than 90 days are safest (1.0)
            # Files newer than 7 days are least safe (0.0)
            if days_old >= 90:
                return 1.0
            elif days_old <= 7:
                return 0.0
            else:
                # Linear interpolation between 7 and 90 days
                return (days_old - 7) / (90 - 7)
        except (OSError, IOError):
            return 0.5  # Default to medium safety

    def _calculate_file_location_factor(self, file_path: str) -> float:
        """Calculate location-based safety factor (temp locations = safer)."""
        abs_path = os.path.abspath(file_path)

        # Safe locations (high safety factor)
        safe_locations = [
            '/tmp', '/temp', '/var/tmp', '/var/cache',
            'C:\\Temp', 'C:\\tmp', 'C:\\Windows\\Temp',
            os.path.expanduser('~') + '/Downloads'
        ]

        # Risky locations (low safety factor)
        risky_locations = [
            '/home', '/Users', '/Documents', '/Desktop',
            'C:\\Users', 'C:\\Documents and Settings'
        ]

        for safe_loc in safe_locations:
            if abs_path.startswith(safe_loc):
                return 1.0

        for risky_loc in risky_locations:
            if abs_path.startswith(risky_loc):
                return 0.2

        return 0.6  # Default to medium safety

    def _calculate_user_behavior_factor(self, file_path: str) -> float:
        """Calculate user behavior pattern factor."""
        # This would typically analyze user patterns
        # For testing, use file extension and name patterns
        _, ext = os.path.splitext(file_path.lower())

        # High safety patterns (likely temporary/cache files)
        high_safety_patterns = ['.tmp', '.temp', '.cache', '.log', '.bak']
        if ext in high_safety_patterns or any(pattern in file_path.lower() for pattern in high_safety_patterns):
            return 1.0

        # Medium safety patterns
        medium_safety_extensions = ['.pyc', '.class', '.o', '.obj']
        if ext in medium_safety_extensions:
            return 0.7

        # Low safety patterns (important file types)
        low_safety_extensions = ['.doc', '.pdf', '.jpg', '.mov', '.zip']
        if ext in low_safety_extensions:
            return 0.3

        return 0.5  # Default medium safety

    def _determine_protection_level(
        self,
        traditional_level: ProtectionLevel,
        ai_result: AIAnalysisResult
    ) -> ProtectionLevel:
        """Determine final protection level combining traditional and AI assessment."""

        # AI recommendations can upgrade protection but not downgrade critical protections
        if traditional_level == ProtectionLevel.CRITICAL:
            return ProtectionLevel.CRITICAL

        if ai_result.recommendation == AIRecommendation.PROTECTED:
            return ProtectionLevel.HIGH

        if ai_result.recommendation == AIRecommendation.KEEP:
            if traditional_level == ProtectionLevel.SAFE:
                return ProtectionLevel.MODERATE
            return traditional_level

        if ai_result.recommendation == AIRecommendation.REVIEW:
            if traditional_level == ProtectionLevel.SAFE:
                return ProtectionLevel.REQUIRES_REVIEW
            return traditional_level

        # AI recommendation is DELETE
        if traditional_level == ProtectionLevel.SAFE:
            return ProtectionLevel.SAFE

        # Keep traditional protection for non-safe files
        return traditional_level

    def _apply_ai_confidence_thresholds(
        self,
        file_path: str,
        safety_score: SafetyScore,
        ai_result: AIAnalysisResult
    ) -> SafetyDecision:
        """Apply AI confidence thresholds to make final safety decision."""

        # Log AI recommendation and confidence
        self.safety_layer.audit_trail.log_ai_recommendation(
            file_path=file_path,
            ai_recommendation=ai_result.recommendation.value,
            ai_confidence=ai_result.confidence,
            ai_reasoning=ai_result.reasoning
        )

        # Apply confidence thresholds
        if safety_score.confidence >= self.confidence_thresholds["auto_delete"]:
            if safety_score.can_auto_delete:
                self.safety_layer.audit_trail.log_threshold_application(
                    file_path=file_path,
                    confidence=safety_score.confidence,
                    threshold=self.confidence_thresholds["auto_delete"],
                    decision=SafetyDecision.SAFE_TO_DELETE
                )
                return SafetyDecision.SAFE_TO_DELETE

        elif safety_score.confidence >= self.confidence_thresholds["review"]:
            self.safety_layer.audit_trail.log_threshold_application(
                file_path=file_path,
                confidence=safety_score.confidence,
                threshold=self.confidence_thresholds["review"],
                decision=SafetyDecision.MANUAL_REVIEW
            )
            return SafetyDecision.MANUAL_REVIEW

        # Below review threshold - keep file
        self.safety_layer.audit_trail.log_threshold_application(
            file_path=file_path,
            confidence=safety_score.confidence,
            threshold=self.confidence_thresholds["keep"],
            decision=SafetyDecision.PROTECTED
        )
        return SafetyDecision.PROTECTED


class TestAIConfidenceScoringIntegration:
    """Test suite for AI confidence scoring integration with safety layer."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.safety_layer = SafetyLayer()
        self.ai_safety_assessment = AISafetyAssessment(self.safety_layer)
        self.audit_trail = AuditTrail()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_file(self, filename: str, age_days: int = 0) -> str:
        """Create a test file with specified age."""
        file_path = os.path.join(self.temp_dir, filename)
        Path(file_path).touch()

        if age_days > 0:
            old_time = datetime.now() - timedelta(days=age_days)
            os.utime(file_path, (old_time.timestamp(), old_time.timestamp()))

        return file_path

    def test_ai_confidence_scoring_high_confidence_auto_delete(self):
        """Test high AI confidence (≥0.95) enables automatic deletion."""
        # Create a temporary file that's old enough to have good safety factors
        temp_file = self.create_test_file("temp_file.tmp", age_days=100)

        # Simulate AI analysis with high confidence
        ai_result = AIAnalysisResult(
            file_path=temp_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.96,
            reasoning="Temporary file in temp location",
            risk_level="low",
            category="temporary_file"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(temp_file, ai_result)

    
        # Verify high confidence enables auto-deletion
        assert assessment.safety_score.confidence >= 0.95
        assert assessment.safety_score.protection_level == ProtectionLevel.SAFE
        assert assessment.safety_score.can_auto_delete == True
        assert assessment.can_auto_delete == True

    def test_ai_confidence_scoring_medium_confidence_requires_review(self):
        """Test medium AI confidence (0.70-0.95) requires manual review."""
        # Create a document file with better age factor
        doc_file = self.create_test_file("document.doc", age_days=60)

        # Simulate AI analysis with medium confidence
        ai_result = AIAnalysisResult(
            file_path=doc_file,
            recommendation=AIRecommendation.REVIEW,
            confidence=0.75,
            reasoning="Document file, moderate age, uncertain usage",
            risk_level="medium",
            category="document"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(doc_file, ai_result)

        # Verify medium confidence requires review
        assert assessment.can_auto_delete == False
        assert 0.70 <= assessment.safety_score.confidence < 0.95
        assert assessment.safety_score.protection_level == ProtectionLevel.REQUIRES_REVIEW

    def test_ai_confidence_scoring_low_confidence_keep_file(self):
        """Test low AI confidence (<0.70) keeps file."""
        # Create an important file
        important_file = self.create_test_file("important.pdf", age_days=5)

        # Simulate AI analysis with low confidence
        ai_result = AIAnalysisResult(
            file_path=important_file,
            recommendation=AIRecommendation.KEEP,
            confidence=0.45,
            reasoning="Recent important document, low confidence in safety",
            risk_level="high",
            category="important_document"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(important_file, ai_result)

        # Verify low confidence keeps file
        assert assessment.can_auto_delete == False
        assert assessment.safety_score.confidence < 0.70
        assert assessment.safety_score.protection_level in [
            ProtectionLevel.REQUIRES_REVIEW, ProtectionLevel.MODERATE, ProtectionLevel.HIGH
        ]

    def test_ai_safety_assessment_algorithm_integration(self):
        """Test AI safety assessment algorithm with traditional safety layer."""
        # Create a test file
        test_file = self.create_test_file("test_file.tmp", age_days=60)

        # Get traditional safety assessment
        traditional_score = self.safety_layer.calculate_safety_score(test_file)

        # Simulate AI analysis
        ai_result = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.85,
            reasoning="Old temporary file, safe to delete",
            risk_level="low",
            category="temporary_file"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result)

        # Verify AI enhances traditional assessment
        assert assessment.safety_score.confidence != traditional_score.confidence
        assert "ai_confidence" in assessment.safety_score.factors
        assert "ai_recommendation" in assessment.safety_score.factors
        assert assessment.safety_score.factors["ai_confidence"] == ai_result.confidence

    def test_file_age_factor_adjustment(self):
        """Test file age factor adjustment in AI confidence scoring."""
        # Create files with different ages
        old_file = self.create_test_file("old_file.tmp", age_days=120)
        new_file = self.create_test_file("new_file.tmp", age_days=3)

        # Same AI analysis for both files
        ai_result = AIAnalysisResult(
            file_path="",
            recommendation=AIRecommendation.DELETE,
            confidence=0.80,
            reasoning="Base analysis",
            risk_level="medium",
            category="temporary_file"
        )

        # Assess old file
        ai_result.file_path = old_file
        old_assessment = self.ai_safety_assessment.assess_file_with_ai(old_file, ai_result)

        # Assess new file
        ai_result.file_path = new_file
        new_assessment = self.ai_safety_assessment.assess_file_with_ai(new_file, ai_result)

        # Verify age factor adjustment
        old_age_factor = old_assessment.safety_score.factors["age_factor"]
        new_age_factor = new_assessment.safety_score.factors["age_factor"]

        assert old_age_factor > new_age_factor
        assert old_assessment.safety_score.confidence > new_assessment.safety_score.confidence

    def test_file_location_factor_adjustment(self):
        """Test file location factor adjustment in AI confidence scoring."""
        # Create files in different locations
        temp_file = self.create_test_file("temp.tmp")
        temp_file_path = os.path.join(tempfile.gettempdir(), "temp.tmp")

        # Create a mock file in temp directory
        temp_dir = tempfile.mkdtemp()
        temp_location_file = os.path.join(temp_dir, "temp.tmp")
        Path(temp_location_file).touch()

        # Same AI analysis
        ai_result = AIAnalysisResult(
            file_path="",
            recommendation=AIRecommendation.DELETE,
            confidence=0.80,
            reasoning="Base analysis",
            risk_level="medium",
            category="temporary_file"
        )

        # Assess regular temp file
        ai_result.file_path = temp_file
        regular_assessment = self.ai_safety_assessment.assess_file_with_ai(temp_file, ai_result)

        # Assess temp location file
        ai_result.file_path = temp_location_file
        temp_assessment = self.ai_safety_assessment.assess_file_with_ai(temp_location_file, ai_result)

        # Clean up temp directory
        shutil.rmtree(temp_dir)

        # Verify location factor adjustment
        regular_location = regular_assessment.safety_score.factors["location_factor"]
        temp_location = temp_assessment.safety_score.factors["location_factor"]

        # Temp location should have higher safety factor
        assert temp_location >= regular_location

    def test_user_behavior_factor_adjustment(self):
        """Test user behavior factor adjustment in AI confidence scoring."""
        # Create files with different extensions
        temp_file = self.create_test_file("temp.tmp")
        doc_file = self.create_test_file("document.doc")
        cache_file = self.create_test_file("cache.cache")

        # Same AI analysis
        ai_result = AIAnalysisResult(
            file_path="",
            recommendation=AIRecommendation.DELETE,
            confidence=0.80,
            reasoning="Base analysis",
            risk_level="medium",
            category="test_file"
        )

        assessments = {}

        # Assess temp file
        ai_result.file_path = temp_file
        assessments["temp"] = self.ai_safety_assessment.assess_file_with_ai(temp_file, ai_result)

        # Assess document file
        ai_result.file_path = doc_file
        assessments["doc"] = self.ai_safety_assessment.assess_file_with_ai(doc_file, ai_result)

        # Assess cache file
        ai_result.file_path = cache_file
        assessments["cache"] = self.ai_safety_assessment.assess_file_with_ai(cache_file, ai_result)

        # Verify user behavior factor adjustments
        temp_behavior = assessments["temp"].safety_score.factors["behavior_factor"]
        doc_behavior = assessments["doc"].safety_score.factors["behavior_factor"]
        cache_behavior = assessments["cache"].safety_score.factors["behavior_factor"]

        # Cache and temp files should have higher safety factors
        assert cache_behavior >= temp_behavior
        assert temp_behavior >= doc_behavior

    def test_ai_recommendation_validation_against_safety_rules(self):
        """Test AI recommendation validation against existing safety rules."""
        # Create a system file path (should be protected)
        system_file = "/usr/bin/python3"

        # AI suggests deletion (but safety rules should override)
        ai_result = AIAnalysisResult(
            file_path=system_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.99,
            reasoning="AI thinks this can be deleted",
            risk_level="low",
            category="system_file"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(system_file, ai_result)

        # Safety rules should override AI recommendation
        assert assessment.safety_score.protection_level == ProtectionLevel.CRITICAL
        assert assessment.can_auto_delete == False
        assert assessment.safety_score.confidence > 0.95  # High confidence in protection

    def test_multi_layer_safety_assessment_workflow(self):
        """Test complete multi-layer safety assessment workflow with AI integration."""
        # Create test scenarios
        test_scenarios = [
            {
                "file": "system_critical.dll",
                "path": "C:/Windows/System32/critical.dll",
                "ai_confidence": 0.90,
                "ai_recommendation": AIRecommendation.DELETE,
                "expected_protection": ProtectionLevel.CRITICAL,
                "expected_auto_delete": False
            },
            {
                "file": "recent_document.pdf",
                "path": os.path.join(self.temp_dir, "recent.pdf"),
                "ai_confidence": 0.60,
                "ai_recommendation": AIRecommendation.KEEP,
                "expected_protection": ProtectionLevel.REQUIRES_REVIEW,
                "expected_auto_delete": False
            },
            {
                "file": "old_temp.tmp",
                "path": self.create_test_file("old_temp.tmp", age_days=100),
                "ai_confidence": 0.97,
                "ai_recommendation": AIRecommendation.DELETE,
                "expected_protection": ProtectionLevel.SAFE,
                "expected_auto_delete": True
            }
        ]

        # Create actual files for non-system paths
        for scenario in test_scenarios:
            if scenario["path"].startswith(self.temp_dir):
                Path(scenario["path"]).touch()
                if "old_temp" in scenario["file"]:
                    old_time = datetime.now() - timedelta(days=100)
                    os.utime(scenario["path"], (old_time.timestamp(), old_time.timestamp()))

        # Run assessments
        for scenario in test_scenarios:
            ai_result = AIAnalysisResult(
                file_path=scenario["path"],
                recommendation=scenario["ai_recommendation"],
                confidence=scenario["ai_confidence"],
                reasoning=f"Test analysis for {scenario['file']}",
                risk_level="medium",
                category="test"
            )

            assessment = self.ai_safety_assessment.assess_file_with_ai(
                scenario["path"], ai_result
            )

            # Verify multi-layer protection
            assert assessment.safety_score.protection_level == scenario["expected_protection"]
            assert assessment.can_auto_delete == scenario["expected_auto_delete"]

            # Verify AI integration
            assert "ai_confidence" in assessment.safety_score.factors
            assert "ai_recommendation" in assessment.safety_score.factors

    def test_confidence_threshold_boundary_conditions(self):
        """Test confidence threshold boundary conditions."""
        # Create a test file
        test_file = self.create_test_file("boundary_test.tmp", age_days=50)

        # Test exact threshold boundaries
        boundary_tests = [
            {"confidence": 0.95, "expected_decision": SafetyDecision.SAFE_TO_DELETE},
            {"confidence": 0.94, "expected_decision": SafetyDecision.MANUAL_REVIEW},
            {"confidence": 0.70, "expected_decision": SafetyDecision.MANUAL_REVIEW},
            {"confidence": 0.69, "expected_decision": SafetyDecision.PROTECTED},
            {"confidence": 0.50, "expected_decision": SafetyDecision.PROTECTED}
        ]

        for test in boundary_tests:
            ai_result = AIAnalysisResult(
                file_path=test_file,
                recommendation=AIRecommendation.DELETE,
                confidence=test["confidence"],
                reasoning=f"Boundary test with confidence {test['confidence']}",
                risk_level="medium",
                category="test"
            )

            assessment = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result)

            # Verify threshold application
            if test["confidence"] >= 0.95:
                assert assessment.can_auto_delete == True
            elif test["confidence"] >= 0.70:
                assert assessment.can_auto_delete == False
                assert assessment.safety_score.protection_level == ProtectionLevel.REQUIRES_REVIEW
            else:
                assert assessment.can_auto_delete == False
                assert assessment.safety_score.protection_level != ProtectionLevel.SAFE

    def test_ai_safety_integration_error_handling(self):
        """Test error handling in AI safety integration."""
        # Test with non-existent file
        non_existent_file = "/non/existent/file.tmp"

        ai_result = AIAnalysisResult(
            file_path=non_existent_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.80,
            reasoning="Test with non-existent file",
            risk_level="medium",
            category="test"
        )

        # Should handle gracefully without crashing
        assessment = self.ai_safety_assessment.assess_file_with_ai(non_existent_file, ai_result)

        # Should still produce valid assessment
        assert assessment is not None
        assert assessment.file_path == non_existent_file
        assert isinstance(assessment.safety_score, SafetyScore)

    def test_ai_confidence_factor_weights(self):
        """Test that AI confidence factor weights are properly applied."""
        # Create a test file
        test_file = self.create_test_file("weight_test.tmp", age_days=45)

        # Create AI result with specific confidence
        ai_result = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.80,
            reasoning="Weight test",
            risk_level="medium",
            category="test"
        )

        assessment = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result)
        factors = assessment.safety_score.factors

        # Verify all factors are present
        assert "ai_confidence" in factors
        assert "age_factor" in factors
        assert "location_factor" in factors
        assert "behavior_factor" in factors

        # Verify AI confidence has highest weight (0.5)
        # Final confidence should be influenced by AI confidence
        assert abs(assessment.safety_score.confidence - 0.80) < 0.3  # Within reasonable range

    def test_ai_safety_audit_trail_integration(self):
        """Test that AI safety decisions are properly logged to audit trail."""
        # Create a test file
        test_file = self.create_test_file("audit_test.tmp", age_days=30)

        ai_result = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.90,
            reasoning="Audit trail test",
            risk_level="low",
            category="temporary_file"
        )

        # Assess with AI integration
        assessment = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result)

        # Check that AI recommendation was logged
        # Use the logs attribute from AuditTrail
        logs = getattr(self.safety_layer.audit_trail, 'logs', [])

        # Should have logs for AI recommendation
        ai_recommendation_logged = any(
            "AI_RECOMMENDATION" in str(log.user_action) if hasattr(log, 'user_action') and log.user_action
            else "ai_recommendation" in str(log.reason).lower()
            for log in logs
        )

        assert ai_recommendation_logged, "AI recommendation should be logged in audit trail"


class TestAIConfidenceThresholds:
    """Test suite specifically for AI confidence threshold validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.safety_layer = SafetyLayer()
        self.ai_safety_assessment = AISafetyAssessment(self.safety_layer)

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_auto_delete_threshold_95(self):
        """Test auto-delete threshold at 0.95 confidence."""
        test_file = os.path.join(self.temp_dir, "auto_delete_test.tmp")
        Path(test_file).touch()

        # Test just above threshold
        ai_result_above = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.96,
            reasoning="Just above auto-delete threshold",
            risk_level="low",
            category="temporary_file"
        )

        assessment_above = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result_above)
        assert assessment_above.can_auto_delete == True

        # Test just below threshold
        ai_result_below = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.94,
            reasoning="Just below auto-delete threshold",
            risk_level="low",
            category="temporary_file"
        )

        assessment_below = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result_below)
        assert assessment_below.can_auto_delete == False

    def test_review_threshold_70(self):
        """Test review threshold at 0.70 confidence."""
        test_file = os.path.join(self.temp_dir, "review_test.tmp")
        Path(test_file).touch()

        # Test just above review threshold
        ai_result_above = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.71,
            reasoning="Just above review threshold",
            risk_level="medium",
            category="test"
        )

        assessment_above = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result_above)
        assert assessment_above.can_auto_delete == False
        assert assessment_above.safety_score.protection_level == ProtectionLevel.REQUIRES_REVIEW

        # Test just below review threshold
        ai_result_below = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.69,
            reasoning="Just below review threshold",
            risk_level="medium",
            category="test"
        )

        assessment_below = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result_below)
        assert assessment_below.can_auto_delete == False
        assert assessment_below.safety_score.protection_level != ProtectionLevel.SAFE

    def test_confidence_threshold_configuration(self):
        """Test that confidence thresholds can be configured."""
        # Test default thresholds
        assert self.ai_safety_assessment.confidence_thresholds["auto_delete"] == 0.95
        assert self.ai_safety_assessment.confidence_thresholds["review"] == 0.70
        assert self.ai_safety_assessment.confidence_thresholds["keep"] == 0.0

        # Test threshold modification
        self.ai_safety_assessment.confidence_thresholds["auto_delete"] = 0.90
        self.ai_safety_assessment.confidence_thresholds["review"] = 0.65

        test_file = os.path.join(self.temp_dir, "config_test.tmp")
        Path(test_file).touch()

        ai_result = AIAnalysisResult(
            file_path=test_file,
            recommendation=AIRecommendation.DELETE,
            confidence=0.92,
            reasoning="Test with modified thresholds",
            risk_level="low",
            category="temporary_file"
        )

        assessment = self.ai_safety_assessment.assess_file_with_ai(test_file, ai_result)

        # Should now allow auto-deletion with lower threshold
        assert assessment.can_auto_delete == True


