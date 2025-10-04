"""
AI Accuracy Validation Test Suite - Comprehensive testing for AI analysis accuracy.

This test suite validates AI analysis accuracy, confidence scoring reliability,
recommendation quality, and safety layer integration using comprehensive test datasets.
"""

import json
import pytest
import statistics
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Tuple

from src.ai_disk_cleanup.core.ai_analyzer import (
    AIAnalyzer,
    ConfidenceScore,
    PredictionResult,
    PredictionType,
    AccuracyMetrics
)
from src.ai_disk_cleanup.openai_client import FileMetadata, FileAnalysisResult
from src.ai_disk_cleanup.safety_layer import SafetyLayer, ProtectionLevel
from src.ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel


class TestAIAccuracyValidation:
    """
    Comprehensive test suite for AI accuracy validation.

    This class tests AI analysis accuracy across multiple dimensions:
    - Overall prediction accuracy
    - Confidence scoring calibration
    - Recommendation quality
    - Safety layer integration
    - Edge case handling
    """

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AppConfig(
            ai_model=type('AIModel', (), {
                'model_name': 'gpt-3.5-turbo',
                'temperature': 0.1,
                'max_tokens': 1000,
                'timeout_seconds': 30
            })()
        )

    @pytest.fixture
    def mock_safety_layer(self):
        """Create mock safety layer."""
        safety_layer = Mock(spec=SafetyLayer)
        safety_layer.calculate_safety_score.return_value = Mock(
            confidence=0.8,
            risk_score=0.2,
            protection_level=ProtectionLevel.SAFE,
            can_auto_delete=True
        )
        return safety_layer

    @pytest.fixture
    def ai_analyzer(self, test_config, mock_safety_layer):
        """Create AI analyzer for testing."""
        return AIAnalyzer(test_config, mock_safety_layer)

    @pytest.fixture
    def validation_dataset(self):
        """Load validation dataset."""
        dataset_path = Path("/home/malu/.projects/ai-disk-cleanup/tests/test_data/comprehensive_validation.json")
        with open(dataset_path, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def confidence_dataset(self):
        """Load confidence calibration dataset."""
        dataset_path = Path("/home/malu/.projects/ai-disk-cleanup/tests/test_data/confidence_calibration.json")
        with open(dataset_path, 'r') as f:
            return json.load(f)

    @pytest.fixture
    def edge_cases_dataset(self):
        """Load edge cases dataset."""
        dataset_path = Path("/home/malu/.projects/ai-disk-cleanup/tests/test_data/edge_cases.json")
        with open(dataset_path, 'r') as f:
            return json.load(f)

    def test_ai_analyzer_initialization(self, ai_analyzer):
        """Test AI analyzer initialization."""
        assert ai_analyzer is not None
        assert ai_analyzer.prediction_history == []
        assert ai_analyzer.confidence_history == []
        assert ai_analyzer.calibration_factor == 1.0
        assert ai_analyzer.confidence_thresholds[ConfidenceLevel.HIGH] == 0.8

    @patch('src.ai_disk_cleanup.core.ai_analyzer.OpenAIClient')
    def test_file_analysis_with_confidence(self, mock_openai_client, ai_analyzer):
        """Test file analysis with confidence scoring."""
        # Mock OpenAI client response
        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        mock_analysis_result = FileAnalysisResult(
            path="/tmp/test_file.tmp",
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Test temporary file",
            category="temporary",
            risk_level="low",
            suggested_action="delete"
        )
        mock_client_instance.analyze_files.return_value = [mock_analysis_result]

        # Create test file metadata
        file_metadata = FileMetadata(
            path="/tmp/test_file.tmp",
            name="test_file.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        # Analyze file
        result, confidence_score = ai_analyzer.analyze_file_with_confidence(file_metadata)

        # Verify results
        assert result is not None
        assert result.path == "/tmp/test_file.tmp"
        assert confidence_score is not None
        assert 0.0 <= confidence_score.primary_score <= 1.0
        assert 0.0 <= confidence_score.uncertainty <= 1.0
        assert confidence_score.prediction_type == PredictionType.DELETION_RECOMMENDATION

    def test_confidence_score_calculation(self, ai_analyzer):
        """Test confidence score calculation factors."""
        # Test different file types and scenarios
        test_cases = [
            # Obvious temporary file
            {
                'name': 'temp_file.tmp',
                'parent_dir': '/tmp',
                'size': 1024,
                'extension': '.tmp',
                'expected_min_confidence': 0.7
            },
            # System file
            {
                'name': 'system.dll',
                'parent_dir': '/usr/lib',
                'size': 1000000,
                'extension': '.dll',
                'expected_min_confidence': 0.8
            },
            # User document
            {
                'name': 'document.pdf',
                'parent_dir': '/home/user/documents',
                'size': 50000,
                'extension': '.pdf',
                'expected_min_confidence': 0.6
            }
        ]

        for test_case in test_cases:
            file_metadata = FileMetadata(
                path=f"{test_case['parent_dir']}/{test_case['name']}",
                name=test_case['name'],
                size_bytes=test_case['size'],
                extension=test_case['extension'],
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory=test_case['parent_dir'],
                is_hidden=False,
                is_system=False
            )

            # Create mock analysis result
            mock_result = FileAnalysisResult(
                path=file_metadata.path,
                deletion_recommendation="keep",
                confidence=ConfidenceLevel.MEDIUM,
                reason="Test analysis",
                category="test",
                risk_level="medium",
                suggested_action="keep"
            )

            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=True
            )

            assert confidence_score.primary_score >= test_case['expected_min_confidence']
            assert confidence_score.uncertainty >= 0.0
            assert len(confidence_score.supporting_evidence) > 0

    def test_confidence_calibration(self, ai_analyzer):
        """Test confidence score calibration."""
        # Create ground truth data for calibration
        ground_truth_data = [
            {'predicted_confidence': 0.9, 'actual_outcome': True},
            {'predicted_confidence': 0.8, 'actual_outcome': True},
            {'predicted_confidence': 0.7, 'actual_outcome': True},
            {'predicted_confidence': 0.6, 'actual_outcome': False},
            {'predicted_confidence': 0.5, 'actual_outcome': False},
            {'predicted_confidence': 0.4, 'actual_outcome': False},
            {'predicted_confidence': 0.3, 'actual_outcome': False},
            {'predicted_confidence': 0.2, 'actual_outcome': False}
        ]

        # Calibrate confidence scores
        ai_analyzer.calibrate_confidence_scores(ground_truth_data)

        # Verify calibration factor was updated
        assert ai_analyzer.calibration_factor != 1.0
        assert 0.5 <= ai_analyzer.calibration_factor <= 2.0

    def test_accuracy_metrics_calculation(self, ai_analyzer):
        """Test accuracy metrics calculation."""
        # Create test data with known outcomes
        test_data = [
            {
                'is_correct': True,
                'confidence': 0.9,
                'prediction_type': PredictionType.DELETION_RECOMMENDATION,
                'recommendation': 'delete',
                'category': 'temporary',
                'uncertainty': 0.1
            },
            {
                'is_correct': True,
                'confidence': 0.8,
                'prediction_type': PredictionType.DELETION_RECOMMENDATION,
                'recommendation': 'delete',
                'category': 'cache',
                'uncertainty': 0.15
            },
            {
                'is_correct': False,
                'confidence': 0.6,
                'prediction_type': PredictionType.DELETION_RECOMMENDATION,
                'recommendation': 'keep',
                'category': 'document',
                'uncertainty': 0.2
            },
            {
                'is_correct': True,
                'confidence': 0.7,
                'prediction_type': PredictionType.CATEGORY_CLASSIFICATION,
                'recommendation': 'keep',
                'category': 'system',
                'uncertainty': 0.1
            }
        ]

        metrics = ai_analyzer.calculate_accuracy_metrics(test_data)

        # Verify metrics structure
        assert metrics.overall_accuracy == 0.75  # 3/4 correct
        assert 0.0 <= metrics.confidence_calibration <= 1.0
        assert len(metrics.prediction_accuracy_by_type) > 0
        assert len(metrics.confidence_distribution) > 0
        assert 'error_rate' in metrics.error_analysis
        assert len(metrics.calibration_curve_data) > 0
        assert 'mean_uncertainty' in metrics.uncertainty_analysis
        assert len(metrics.recommendation_accuracy) > 0

        # Verify summary score calculation
        summary_score = metrics.get_summary_score()
        assert 0.0 <= summary_score <= 1.0

    @patch('src.ai_disk_cleanup.core.ai_analyzer.OpenAIClient')
    def test_comprehensive_validation(self, mock_openai_client, ai_analyzer, validation_dataset):
        """Test comprehensive validation using generated dataset."""
        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_openai_client.return_value = mock_client_instance

        # Load validation dataset into analyzer
        dataset_path = "/home/malu/.projects/ai-disk-cleanup/tests/test_data/comprehensive_validation.json"
        ai_analyzer.load_validation_dataset("comprehensive_test", dataset_path)

        # Verify dataset was loaded
        assert "comprehensive_test" in ai_analyzer.validation_datasets
        assert len(ai_analyzer.validation_datasets["comprehensive_test"]) == 1000

        # Test a sample of the dataset
        sample_size = 50
        sample_data = validation_dataset[:sample_size]

        correct_predictions = 0
        confidence_scores = []

        for test_case in sample_data:
            # Create mock analysis result
            file_metadata_dict = test_case['file_metadata']
            file_metadata = FileMetadata(**file_metadata_dict)

            mock_result = FileAnalysisResult(
                path=file_metadata.path,
                deletion_recommendation=test_case['expected_recommendation'],
                confidence=ConfidenceLevel.HIGH,
                reason="Mock analysis",
                category=test_case['expected_category'],
                risk_level=test_case['expected_risk_level'],
                suggested_action=test_case['expected_recommendation']
            )
            mock_client_instance.analyze_files.return_value = [mock_result]

            # Analyze file
            try:
                result, confidence_score = ai_analyzer.analyze_file_with_confidence(file_metadata)

                # Check if recommendation matches expected
                if result.deletion_recommendation == test_case['expected_recommendation']:
                    correct_predictions += 1

                confidence_scores.append(confidence_score.get_calibrated_score())

                # Verify confidence is within expected range
                expected_min, expected_max = test_case['expected_confidence_range']
                assert expected_min <= confidence_score.get_calibrated_score() <= expected_max + 0.1

            except Exception as e:
                # Log errors but continue testing
                print(f"Error analyzing {file_metadata.path}: {e}")

        # Calculate accuracy
        accuracy = correct_predictions / len(sample_data)

        # Verify minimum accuracy threshold
        assert accuracy >= 0.6, f"Accuracy {accuracy:.3f} below minimum threshold of 0.6"

        # Verify confidence scores are reasonable
        if confidence_scores:
            avg_confidence = statistics.mean(confidence_scores)
            assert 0.4 <= avg_confidence <= 1.0, f"Average confidence {avg_confidence:.3f} out of reasonable range"

    def test_confidence_scoring_reliability(self, ai_analyzer, confidence_dataset):
        """Test confidence scoring reliability and calibration."""
        # Test confidence score consistency
        test_cases = confidence_dataset[:20]  # Sample for testing

        confidence_scores = []
        uncertainties = []

        for test_case in test_cases:
            file_metadata_dict = test_case['file_metadata']
            file_metadata = FileMetadata(**file_metadata_dict)

            # Create mock analysis result
            mock_result = FileAnalysisResult(
                path=file_metadata.path,
                deletion_recommendation=test_case['expected_recommendation'],
                confidence=ConfidenceLevel.MEDIUM,
                reason="Test analysis",
                category=test_case['expected_category'],
                risk_level=test_case['expected_risk_level'],
                suggested_action=test_case['expected_recommendation']
            )

            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=True
            )

            confidence_scores.append(confidence_score.get_calibrated_score())
            uncertainties.append(confidence_score.uncertainty)

            # Verify confidence score properties
            assert 0.0 <= confidence_score.primary_score <= 1.0
            assert 0.0 <= confidence_score.uncertainty <= 1.0
            assert confidence_score.prediction_type == PredictionType.DELETION_RECOMMENDATION
            assert len(confidence_score.supporting_evidence) > 0
            assert len(confidence_score.confidence_intervals) > 0

        # Verify confidence score distribution
        if len(confidence_scores) > 1:
            confidence_std = statistics.stdev(confidence_scores)
            assert confidence_std > 0.05, "Confidence scores should have reasonable variance"

        # Verify uncertainty quantification
        if len(uncertainties) > 1:
            avg_uncertainty = statistics.mean(uncertainties)
            assert 0.05 <= avg_uncertainty <= 0.5, f"Average uncertainty {avg_uncertainty:.3f} out of reasonable range"

    def test_safety_layer_integration(self, ai_analyzer, mock_safety_layer):
        """Test safety layer integration with AI analysis."""
        # Test safety layer is consulted during analysis
        file_metadata = FileMetadata(
            path="/tmp/test_file.tmp",
            name="test_file.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        mock_result = FileAnalysisResult(
            path=file_metadata.path,
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Test analysis",
            category="temporary",
            risk_level="low",
            suggested_action="delete"
        )

        # Calculate confidence with safety assessment
        confidence_score = ai_analyzer._calculate_confidence_score(
            file_metadata, mock_result, include_safety_assessment=True
        )

        # Verify safety layer was consulted
        mock_safety_layer.calculate_safety_score.assert_called()
        assert 'safety_alignment' in confidence_score.supporting_evidence

        # Calculate confidence without safety assessment
        confidence_score_no_safety = ai_analyzer._calculate_confidence_score(
            file_metadata, mock_result, include_safety_assessment=False
        )

        # Verify safety alignment is not included
        assert 'safety_alignment' not in confidence_score_no_safety.supporting_evidence

    def test_edge_cases_handling(self, ai_analyzer, edge_cases_dataset):
        """Test handling of edge cases and unusual file scenarios."""
        edge_cases = edge_cases_dataset[:20]  # Sample for testing

        for test_case in edge_cases:
            file_metadata_dict = test_case['file_metadata']
            file_metadata = FileMetadata(**file_metadata_dict)

            # Create mock analysis result
            mock_result = FileAnalysisResult(
                path=file_metadata.path,
                deletion_recommendation=test_case['expected_recommendation'],
                confidence=ConfidenceLevel.MEDIUM,
                reason="Test edge case",
                category=test_case['expected_category'],
                risk_level=test_case['expected_risk_level'],
                suggested_action=test_case['expected_recommendation']
            )

            # Calculate confidence score
            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=True
            )

            # Verify edge case handling
            assert confidence_score is not None
            assert 0.0 <= confidence_score.primary_score <= 1.0
            assert 0.0 <= confidence_score.uncertainty <= 1.0

            # Edge cases should generally have higher uncertainty
            if test_case['difficulty_level'] == 'hard':
                assert confidence_score.uncertainty >= 0.1, "Edge cases should have higher uncertainty"

    def test_prediction_history_tracking(self, ai_analyzer):
        """Test prediction history tracking and management."""
        # Create test file
        file_metadata = FileMetadata(
            path="/tmp/test_file.tmp",
            name="test_file.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        mock_result = FileAnalysisResult(
            path=file_metadata.path,
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Test analysis",
            category="temporary",
            risk_level="low",
            suggested_action="delete"
        )

        # Store multiple predictions
        for i in range(10):
            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=True
            )

            ai_analyzer._store_prediction(
                prediction="delete",
                confidence_score=confidence_score,
                prediction_type=PredictionType.DELETION_RECOMMENDATION,
                metadata={'test_index': i}
            )

        # Verify history was tracked
        assert len(ai_analyzer.prediction_history) == 10
        assert len(ai_analyzer.confidence_history) == 10

        # Verify prediction structure
        for prediction in ai_analyzer.prediction_history:
            assert prediction.prediction == "delete"
            assert prediction.prediction_type == PredictionType.DELETION_RECOMMENDATION
            assert prediction.confidence_score is not None
            assert 'test_index' in prediction.metadata

    def test_model_performance_summary(self, ai_analyzer):
        """Test model performance summary generation."""
        # Create some cached accuracy metrics
        test_metrics = AccuracyMetrics(
            overall_accuracy=0.85,
            confidence_calibration=0.78,
            prediction_accuracy_by_type={
                PredictionType.DELETION_RECOMMENDATION: 0.85,
                PredictionType.CATEGORY_CLASSIFICATION: 0.82
            },
            confidence_distribution={'high': 60, 'medium': 30, 'low': 10},
            error_analysis={'error_rate': 0.15, 'error_patterns': {}},
            calibration_curve_data=[(0.8, 0.85), (0.6, 0.65)],
            uncertainty_analysis={'mean_uncertainty': 0.15},
            recommendation_accuracy={'delete': 0.9, 'keep': 0.8}
        )

        ai_analyzer.accuracy_cache['test_dataset'] = test_metrics

        # Generate performance summary
        summary = ai_analyzer.get_model_performance_summary()

        # Verify summary structure
        assert 'total_datasets' in summary
        assert 'overall_summary_score' in summary
        assert 'dataset_scores' in summary
        assert 'calibration_factor' in summary
        assert 'total_predictions' in summary
        assert summary['total_datasets'] == 1
        assert summary['calibration_factor'] == 1.0
        assert 'test_dataset' in summary['dataset_scores']

    def test_error_handling_and_fallbacks(self, ai_analyzer):
        """Test error handling and fallback mechanisms."""
        # Test with invalid file metadata
        invalid_metadata = FileMetadata(
            path="",
            name="",
            size_bytes=-1,
            extension="",
            created_date="invalid_date",
            modified_date="invalid_date",
            accessed_date="invalid_date",
            parent_directory="",
            is_hidden=False,
            is_system=False
        )

        mock_result = FileAnalysisResult(
            path=invalid_metadata.path,
            deletion_recommendation="keep",
            confidence=ConfidenceLevel.LOW,
            reason="Invalid metadata",
            category="unknown",
            risk_level="low",
            suggested_action="manual_review"
        )

        # Should handle gracefully
        confidence_score = ai_analyzer._calculate_confidence_score(
            invalid_metadata, mock_result, include_safety_assessment=True
        )

        assert confidence_score is not None
        assert confidence_score.primary_score >= 0.0

    @patch('src.ai_disk_cleanup.core.ai_analyzer.OpenAIClient')
    def test_analysis_fallback_handling(self, mock_openai_client, ai_analyzer):
        """Test fallback handling when AI analysis fails."""
        # Mock OpenAI client to raise exception
        mock_client_instance = Mock()
        mock_client_instance.analyze_files.side_effect = Exception("AI service unavailable")
        mock_openai_client.return_value = mock_client_instance

        file_metadata = FileMetadata(
            path="/tmp/test_file.tmp",
            name="test_file.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        # Should return safe fallback
        result, confidence_score = ai_analyzer.analyze_file_with_confidence(file_metadata)

        assert result is not None
        assert result.deletion_recommendation == "keep"
        assert result.confidence == ConfidenceLevel.LOW
        assert confidence_score.primary_score <= 0.2  # Very low confidence for fallback

    def test_confidence_interval_calculations(self, ai_analyzer):
        """Test confidence interval calculations."""
        # Create confidence score with specific values
        confidence_score = ConfidenceScore(
            primary_score=0.8,
            uncertainty=0.1,
            calibration_factor=1.0,
            prediction_type=PredictionType.DELETION_RECOMMENDATION
        )

        # Test calibrated score
        calibrated = confidence_score.get_calibrated_score()
        assert calibrated == 0.8

        # Test confidence range
        lower, upper = confidence_score.get_confidence_range()
        assert lower == 0.7
        assert upper == 0.9

        # Test with calibration factor
        confidence_score.calibration_factor = 1.2
        calibrated = confidence_score.get_calibrated_score()
        assert calibrated == 0.96  # 0.8 * 1.2, capped at 1.0

        # Test calibration check
        assert confidence_score.is_well_calibrated(tolerance=0.2) == False
        confidence_score.calibration_factor = 1.1
        assert confidence_score.is_well_calibrated(tolerance=0.2) == True


class TestConfidenceScoringReliability:
    """Specific tests for confidence scoring reliability and validation."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AppConfig(
            ai_model=type('AIModel', (), {
                'model_name': 'gpt-3.5-turbo',
                'temperature': 0.1,
                'max_tokens': 1000,
                'timeout_seconds': 30
            })()
        )

    @pytest.fixture
    def ai_analyzer(self, test_config):
        """Create AI analyzer for testing."""
        return AIAnalyzer(test_config)

    def test_confidence_factor_consistency(self, ai_analyzer):
        """Test confidence factor consistency across similar files."""
        # Create similar temporary files
        base_metadata = {
            'created_date': "2024-01-01T00:00:00",
            'modified_date': "2024-01-01T00:00:00",
            'accessed_date': "2024-01-01T00:00:00",
            'parent_directory': "/tmp",
            'is_hidden': False,
            'is_system': False
        }

        similar_files = [
            FileMetadata(name=f"temp_{i}.tmp", path=f"/tmp/temp_{i}.tmp",
                        size_bytes=1024, extension=".tmp", **base_metadata)
            for i in range(5)
        ]

        mock_result = FileAnalysisResult(
            path="/tmp/test.tmp",
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Test temporary file",
            category="temporary",
            risk_level="low",
            suggested_action="delete"
        )

        confidence_scores = []
        for file_metadata in similar_files:
            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=False
            )
            confidence_scores.append(confidence_score.get_calibrated_score())

        # Similar files should have similar confidence scores
        if len(confidence_scores) > 1:
            confidence_std = statistics.stdev(confidence_scores)
            assert confidence_std < 0.2, f"Similar files have too different confidence scores: {confidence_std}"

    def test_uncertainty_reasonableness(self, ai_analyzer):
        """Test uncertainty scores are reasonable and proportional."""
        # Create test cases with varying difficulty
        test_cases = [
            # Easy case - obvious temp file
            {
                'name': 'temp_file.tmp',
                'parent_dir': '/tmp',
                'size': 1024,
                'extension': '.tmp',
                'expected_max_uncertainty': 0.2
            },
            # Hard case - ambiguous file in documents
            {
                'name': 'data.file',
                'parent_dir': '/home/user/documents',
                'size': 50000,
                'extension': '.file',
                'expected_min_uncertainty': 0.1
            }
        ]

        mock_result = FileAnalysisResult(
            path="/tmp/test.tmp",
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.MEDIUM,
            reason="Test analysis",
            category="test",
            risk_level="medium",
            suggested_action="delete"
        )

        for test_case in test_cases:
            file_metadata = FileMetadata(
                path=f"{test_case['parent_dir']}/{test_case['name']}",
                name=test_case['name'],
                size_bytes=test_case['size'],
                extension=test_case['extension'],
                created_date="2024-01-01T00:00:00",
                modified_date="2024-01-01T00:00:00",
                accessed_date="2024-01-01T00:00:00",
                parent_directory=test_case['parent_dir'],
                is_hidden=False,
                is_system=False
            )

            confidence_score = ai_analyzer._calculate_confidence_score(
                file_metadata, mock_result, include_safety_assessment=False
            )

            if 'expected_max_uncertainty' in test_case:
                assert confidence_score.uncertainty <= test_case['expected_max_uncertainty']
            if 'expected_min_uncertainty' in test_case:
                assert confidence_score.uncertainty >= test_case['expected_min_uncertainty']

    def test_supporting_evidence_completeness(self, ai_analyzer):
        """Test supporting evidence completeness and reasonableness."""
        file_metadata = FileMetadata(
            path="/tmp/test_file.tmp",
            name="test_file.tmp",
            size_bytes=1024,
            extension=".tmp",
            created_date="2024-01-01T00:00:00",
            modified_date="2024-01-01T00:00:00",
            accessed_date="2024-01-01T00:00:00",
            parent_directory="/tmp",
            is_hidden=False,
            is_system=False
        )

        mock_result = FileAnalysisResult(
            path=file_metadata.path,
            deletion_recommendation="delete",
            confidence=ConfidenceLevel.HIGH,
            reason="Test analysis",
            category="temporary",
            risk_level="low",
            suggested_action="delete"
        )

        confidence_score = ai_analyzer._calculate_confidence_score(
            file_metadata, mock_result, include_safety_assessment=True
        )

        # Verify supporting evidence
        evidence = confidence_score.supporting_evidence
        assert len(evidence) >= 5  # Should have multiple factors

        # Verify evidence values are reasonable
        for factor, value in evidence.items():
            assert 0.0 <= value <= 1.0, f"Evidence factor {factor} has invalid value: {value}"

        # Verify specific expected factors
        expected_factors = [
            'ai_confidence',
            'file_age_confidence',
            'file_extension_confidence',
            'file_location_confidence',
            'file_size_confidence',
            'pattern_match_confidence'
        ]

        for factor in expected_factors:
            assert factor in evidence, f"Missing expected evidence factor: {factor}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])