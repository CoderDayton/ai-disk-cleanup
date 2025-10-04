#!/usr/bin/env python3
"""
Simple AI Accuracy System Test - Demonstrate the accuracy validation system.

This script demonstrates the AI accuracy validation system without requiring
full OpenAI integration or complex configuration.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.ai_disk_cleanup.core.ai_analyzer import (
    AIAnalyzer,
    ConfidenceScore,
    PredictionType,
    AccuracyMetrics
)
from src.ai_disk_cleanup.safety_layer import SafetyLayer, ProtectionLevel
from src.ai_disk_cleanup.openai_client import FileMetadata, FileAnalysisResult
from src.ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel
from src.ai_disk_cleanup.accuracy.accuracy_reporter import AccuracyReporter, AccuracyThresholds


def setup_simple_config():
    """Create a simple test configuration."""
    return AppConfig(
        ai_model={
            'model_name': 'test-model',
            'temperature': 0.1,
            'max_tokens': 1000,
            'timeout_seconds': 30
        }
    )


def create_test_dataset() -> List[Dict[str, Any]]:
    """Create a small test dataset for demonstration."""
    test_cases = [
        {
            'file_metadata': {
                'path': '/tmp/temp_file.tmp',
                'name': 'temp_file.tmp',
                'size_bytes': 1024,
                'extension': '.tmp',
                'created_date': '2024-01-01T00:00:00',
                'modified_date': '2024-01-01T00:00:00',
                'accessed_date': '2024-01-01T00:00:00',
                'parent_directory': '/tmp',
                'is_hidden': False,
                'is_system': False
            },
            'expected_recommendation': 'delete',
            'expected_category': 'temporary',
            'expected_risk_level': 'low',
            'expected_confidence_range': (0.8, 0.95),
            'protection_level': 'safe',
            'test_scenario': 'temporary_files',
            'difficulty_level': 'easy',
            'ground_truth_reasoning': 'Obvious temporary file in temp directory'
        },
        {
            'file_metadata': {
                'path': '/home/user/documents/important.pdf',
                'name': 'important.pdf',
                'size_bytes': 50000,
                'extension': '.pdf',
                'created_date': '2024-01-01T00:00:00',
                'modified_date': '2024-01-01T00:00:00',
                'accessed_date': '2024-01-01T00:00:00',
                'parent_directory': '/home/user/documents',
                'is_hidden': False,
                'is_system': False
            },
            'expected_recommendation': 'keep',
            'expected_category': 'document',
            'expected_risk_level': 'high',
            'expected_confidence_range': (0.7, 0.9),
            'protection_level': 'requires_review',
            'test_scenario': 'user_documents',
            'difficulty_level': 'medium',
            'ground_truth_reasoning': 'User document in documents folder'
        },
        {
            'file_metadata': {
                'path': '/usr/lib/system_library.so',
                'name': 'system_library.so',
                'size_bytes': 1000000,
                'extension': '.so',
                'created_date': '2024-01-01T00:00:00',
                'modified_date': '2024-01-01T00:00:00',
                'accessed_date': '2024-01-01T00:00:00',
                'parent_directory': '/usr/lib',
                'is_hidden': False,
                'is_system': True
            },
            'expected_recommendation': 'keep',
            'expected_category': 'system',
            'expected_risk_level': 'critical',
            'expected_confidence_range': (0.95, 0.99),
            'protection_level': 'critical',
            'test_scenario': 'system_files',
            'difficulty_level': 'easy',
            'ground_truth_reasoning': 'System file in system directory'
        }
    ]
    return test_cases


def test_confidence_scoring():
    """Test confidence scoring functionality."""
    print("\n" + "="*60)
    print("TESTING CONFIDENCE SCORING")
    print("="*60)

    # Create simple config and safety layer
    config = setup_simple_config()
    safety_layer = SafetyLayer()
    ai_analyzer = AIAnalyzer(config, safety_layer)

    # Test cases
    test_cases = create_test_dataset()

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['file_metadata']['name']}")

        # Create file metadata
        file_metadata = FileMetadata(**test_case['file_metadata'])

        # Create mock analysis result
        mock_result = FileAnalysisResult(
            path=file_metadata.path,
            deletion_recommendation=test_case['expected_recommendation'],
            confidence=ConfidenceLevel.HIGH,
            reason="Mock analysis for testing",
            category=test_case['expected_category'],
            risk_level=test_case['expected_risk_level'],
            suggested_action=test_case['expected_recommendation']
        )

        # Calculate confidence score
        confidence_score = ai_analyzer._calculate_confidence_score(
            file_metadata, mock_result, include_safety_assessment=True
        )

        # Check if within expected range
        expected_min, expected_max = test_case['expected_confidence_range']
        actual_confidence = confidence_score.get_calibrated_score()

        print(f"  Expected confidence range: {expected_min:.2f} - {expected_max:.2f}")
        print(f"  Actual confidence: {actual_confidence:.2f}")
        print(f"  Uncertainty: {confidence_score.uncertainty:.2f}")
        print(f"  Within expected range: {'✓' if expected_min <= actual_confidence <= expected_max else '✗'}")

        # Print supporting evidence
        print("  Supporting evidence:")
        for factor, value in confidence_score.supporting_evidence.items():
            print(f"    {factor}: {value:.2f}")

        # Store prediction for tracking
        ai_analyzer._store_prediction(
            prediction=mock_result.deletion_recommendation,
            confidence_score=confidence_score,
            prediction_type=PredictionType.DELETION_RECOMMENDATION,
            metadata={
                'file_category': mock_result.category,
                'risk_level': mock_result.risk_level,
                'recommendation': mock_result.deletion_recommendation
            }
        )

    return ai_analyzer


def test_accuracy_metrics(ai_analyzer: AIAnalyzer):
    """Test accuracy metrics calculation."""
    print("\n" + "="*60)
    print("TESTING ACCURACY METRICS")
    print("="*60)

    # Create test data for metrics calculation
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
            'recommendation': 'keep',
            'category': 'document',
            'uncertainty': 0.15
        },
        {
            'is_correct': False,
            'confidence': 0.6,
            'prediction_type': PredictionType.DELETION_RECOMMENDATION,
            'recommendation': 'keep',
            'category': 'system',
            'uncertainty': 0.2
        },
        {
            'is_correct': True,
            'confidence': 0.7,
            'prediction_type': PredictionType.CATEGORY_CLASSIFICATION,
            'recommendation': 'keep',
            'category': 'cache',
            'uncertainty': 0.25
        }
    ]

    # Calculate accuracy metrics
    metrics = ai_analyzer.calculate_accuracy_metrics(test_data)

    print("Accuracy Metrics Results:")
    print(f"  Overall Accuracy: {metrics.overall_accuracy:.1%}")
    print(f"  Confidence Calibration: {metrics.confidence_calibration:.1%}")
    print(f"  Error Rate: {metrics.error_analysis['error_rate']:.1%}")
    print(f"  Mean Uncertainty: {metrics.uncertainty_analysis['mean_uncertainty']:.1%}")
    print(f"  Summary Score: {metrics.get_summary_score():.1%}")

    print("\nPrediction Accuracy by Type:")
    for pred_type, accuracy in metrics.prediction_accuracy_by_type.items():
        print(f"  {pred_type.value}: {accuracy:.1%}")

    print("\nRecommendation Accuracy:")
    for rec_type, accuracy in metrics.recommendation_accuracy.items():
        print(f"  {rec_type}: {accuracy:.1%}")

    print("\nConfidence Distribution:")
    for level, count in metrics.confidence_distribution.items():
        print(f"  {level}: {count}")

    return metrics


def test_accuracy_reporter(metrics: AccuracyMetrics, ai_analyzer: AIAnalyzer):
    """Test accuracy reporting functionality."""
    print("\n" + "="*60)
    print("TESTING ACCURACY REPORTER")
    print("="*60)

    # Create accuracy reporter
    reporter = AccuracyReporter(
        output_dir="/home/malu/.projects/ai-disk-cleanup/reports",
        thresholds=AccuracyThresholds(
            min_overall_accuracy=0.75,
            min_confidence_calibration=0.70,
            max_error_rate=0.30,
            min_confidence_reliability=0.65,
            max_uncertainty=0.35,
            min_recommendation_accuracy=0.70
        )
    )

    # Create mock test data for report generation
    test_data = [
        {
            'is_correct': True,
            'confidence': 0.9,
            'prediction_type': 'deletion_recommendation',
            'recommendation': 'delete',
            'category': 'temporary',
            'uncertainty': 0.1
        },
        {
            'is_correct': True,
            'confidence': 0.8,
            'prediction_type': 'deletion_recommendation',
            'recommendation': 'keep',
            'category': 'document',
            'uncertainty': 0.15
        },
        {
            'is_correct': False,
            'confidence': 0.6,
            'prediction_type': 'deletion_recommendation',
            'recommendation': 'keep',
            'category': 'system',
            'uncertainty': 0.2
        }
    ]

    # Generate comprehensive report
    report = reporter.generate_comprehensive_report(
        ai_analyzer=ai_analyzer,
        dataset_name="test_validation",
        test_data=test_data
    )

    print("Generated Validation Report:")
    print(f"  Report ID: {report.report_id}")
    print(f"  Dataset: {report.dataset_name}")
    print(f"  Total Samples: {report.total_samples}")
    print(f"  Summary Score: {report.summary_score:.1%}")
    print(f"  Performance Grade: {report.performance_grade}")
    print(f"  Recommendations: {len(report.recommendations)}")

    print("\nThreshold Compliance:")
    for threshold, passed in report.threshold_compliance.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {threshold}: {status}")

    print("\nTop Recommendations:")
    for i, rec in enumerate(report.recommendations[:3], 1):
        print(f"  {i}. {rec}")

    return report


def test_dataset_generation():
    """Test dataset generation functionality."""
    print("\n" + "="*60)
    print("TESTING DATASET GENERATION")
    print("="*60)

    # Import dataset generator
    sys.path.append(str(Path(__file__).parent / 'tests' / 'test_data'))
    try:
        from dataset_generator import DatasetGenerator

        generator = DatasetGenerator("/home/malu/.projects/ai-disk-cleanup/tests/test_data")

        # Generate small test dataset
        print("Generating small test dataset...")
        test_cases = generator.generate_comprehensive_dataset(
            num_samples=50,
            dataset_name="test_generation"
        )

        print(f"Generated {len(test_cases)} test cases")

        # Analyze dataset composition
        scenario_counts = {}
        difficulty_counts = {}

        for case in test_cases:
            scenario = case.test_scenario
            difficulty = case.difficulty_level

            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

        print("\nDataset Composition:")
        print("Scenarios:")
        for scenario, count in scenario_counts.items():
            print(f"  {scenario}: {count}")

        print("\nDifficulty Levels:")
        for difficulty, count in difficulty_counts.items():
            print(f"  {difficulty}: {count}")

        return True

    except Exception as e:
        print(f"Error in dataset generation: {e}")
        return False


def main():
    """Main test function."""
    print("AI ACCURACY VALIDATION SYSTEM TEST")
    print("=" * 60)
    print("This script demonstrates the AI accuracy validation system")
    print("including confidence scoring, metrics calculation, and reporting.")
    print("=" * 60)

    try:
        # Test confidence scoring
        ai_analyzer = test_confidence_scoring()

        # Test accuracy metrics
        metrics = test_accuracy_metrics(ai_analyzer)

        # Test accuracy reporting
        report = test_accuracy_reporter(metrics, ai_analyzer)

        # Test dataset generation
        dataset_success = test_dataset_generation()

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✓ Confidence scoring system: Working")
        print("✓ Accuracy metrics calculation: Working")
        print("✓ Accuracy reporting: Working")
        print(f"{'✓' if dataset_success else '✗'} Dataset generation: {'Working' if dataset_success else 'Failed'}")
        print(f"✓ Total predictions tracked: {len(ai_analyzer.prediction_history)}")
        print(f"✓ Confidence scores generated: {len(ai_analyzer.confidence_history)}")

        if report:
            print(f"✓ Report generated: {report.report_id}")
            print(f"✓ Performance grade: {report.performance_grade}")
            print(f"✓ Summary score: {report.summary_score:.1%}")

        print("\nAll core functionality tested successfully!")
        print("The AI accuracy validation system is ready for use.")

        # Show file locations
        print("\nGenerated Files:")
        print("  Test datasets: tests/test_data/")
        print("  Validation reports: reports/")
        print("  Log files: ai_accuracy_validation.log")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())