"""
AI Analyzer Module - Core AI analysis with confidence scoring and accuracy validation.

This module provides comprehensive AI analysis capabilities for file cleanup decisions
with enhanced confidence scoring, accuracy metrics, and validation capabilities.
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import re

from ..openai_client import OpenAIClient, FileMetadata, FileAnalysisResult
from ..safety_layer import SafetyLayer, SafetyScore, ProtectionLevel
from ..core.config_models import AppConfig, ConfidenceLevel


class PredictionType(Enum):
    """Types of AI predictions."""
    DELETION_RECOMMENDATION = "deletion_recommendation"
    CATEGORY_CLASSIFICATION = "category_classification"
    RISK_ASSESSMENT = "risk_assessment"
    CONFIDENCE_SCORE = "confidence_score"


class ValidationMetric(Enum):
    """Validation metrics for AI accuracy."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    ERROR_RATE = "error_rate"


@dataclass
class ConfidenceScore:
    """Enhanced confidence score with calibration and uncertainty quantification."""

    primary_score: float  # 0.0 to 1.0
    uncertainty: float  # Standard deviation or uncertainty estimate
    calibration_factor: float  # Calibration adjustment factor
    prediction_type: PredictionType
    supporting_evidence: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    historical_accuracy: Optional[float] = None

    def __post_init__(self):
        """Validate confidence score values."""
        if not 0.0 <= self.primary_score <= 1.0:
            raise ValueError("Primary confidence score must be between 0.0 and 1.0")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("Uncertainty must be between 0.0 and 1.0")
        if not 0.0 <= self.calibration_factor <= 2.0:
            raise ValueError("Calibration factor must be between 0.0 and 2.0")

    def get_calibrated_score(self) -> float:
        """Get calibrated confidence score."""
        calibrated = self.primary_score * self.calibration_factor
        return min(1.0, max(0.0, calibrated))

    def get_confidence_range(self) -> Tuple[float, float]:
        """Get confidence range with uncertainty."""
        calibrated = self.get_calibrated_score()
        lower = max(0.0, calibrated - self.uncertainty)
        upper = min(1.0, calibrated + self.uncertainty)
        return (lower, upper)

    def is_well_calibrated(self, tolerance: float = 0.1) -> bool:
        """Check if confidence score is well calibrated."""
        return abs(1.0 - self.calibration_factor) <= tolerance


@dataclass
class PredictionResult:
    """Single prediction result with metadata."""
    prediction: Any
    confidence_score: ConfidenceScore
    ground_truth: Optional[Any] = None
    is_correct: Optional[bool] = None
    prediction_type: PredictionType = PredictionType.DELETION_RECOMMENDATION
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AccuracyMetrics:
    """Comprehensive accuracy metrics for AI performance evaluation."""

    overall_accuracy: float
    confidence_calibration: float
    prediction_accuracy_by_type: Dict[PredictionType, float]
    confidence_distribution: Dict[str, int]
    error_analysis: Dict[str, Any]
    calibration_curve_data: List[Tuple[float, float]]
    uncertainty_analysis: Dict[str, float]
    recommendation_accuracy: Dict[str, float]

    def get_summary_score(self) -> float:
        """Get overall summary score."""
        weights = {
            'accuracy': 0.3,
            'calibration': 0.25,
            'uncertainty_quality': 0.2,
            'recommendation_quality': 0.25
        }

        uncertainty_score = 1.0 - self.uncertainty_analysis.get('mean_uncertainty', 0.5)
        rec_score = statistics.mean(self.recommendation_accuracy.values()) if self.recommendation_accuracy else 0.5

        return (
            self.overall_accuracy * weights['accuracy'] +
            self.confidence_calibration * weights['calibration'] +
            uncertainty_score * weights['uncertainty_quality'] +
            rec_score * weights['recommendation_quality']
        )


class AIAnalyzer:
    """
    Enhanced AI analyzer with confidence scoring and accuracy validation capabilities.

    This class provides comprehensive AI analysis for file cleanup decisions,
    including confidence scoring, uncertainty quantification, and accuracy validation.
    """

    def __init__(self, config: AppConfig, safety_layer: Optional[SafetyLayer] = None):
        """Initialize AI analyzer with configuration and safety layer."""
        self.config = config
        self.safety_layer = safety_layer or SafetyLayer()
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
        self.openai_client = OpenAIClient(config)

        # Accuracy tracking
        self.prediction_history: List[PredictionResult] = []
        self.accuracy_cache: Dict[str, AccuracyMetrics] = {}
        self.confidence_history: List[ConfidenceScore] = []

        # Confidence scoring parameters
        self.confidence_thresholds = {
            ConfidenceLevel.LOW: 0.3,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.VERY_HIGH: 0.95
        }

        # Calibration parameters
        self.calibration_samples: List[Tuple[float, bool]] = []
        self.calibration_factor = 1.0

        # Validation datasets
        self.validation_datasets: Dict[str, List[Dict[str, Any]]] = {}

    def analyze_file_with_confidence(
        self,
        file_metadata: FileMetadata,
        include_safety_assessment: bool = True
    ) -> Tuple[FileAnalysisResult, ConfidenceScore]:
        """
        Analyze a single file with comprehensive confidence scoring.

        Args:
            file_metadata: File metadata to analyze
            include_safety_assessment: Whether to include safety layer assessment

        Returns:
            Tuple of (analysis_result, confidence_score)
        """
        try:
            # Get base AI analysis
            analysis_results = self.openai_client.analyze_files([file_metadata])

            if not analysis_results:
                raise ValueError("No analysis results returned from AI")

            base_result = analysis_results[0]

            # Calculate comprehensive confidence score
            confidence_score = self._calculate_confidence_score(
                file_metadata,
                base_result,
                include_safety_assessment
            )

            # Enhance result with confidence information
            enhanced_result = self._enhance_analysis_result(
                base_result,
                confidence_score
            )

            # Store prediction for accuracy tracking
            self._store_prediction(
                prediction=base_result.deletion_recommendation,
                confidence_score=confidence_score,
                prediction_type=PredictionType.DELETION_RECOMMENDATION,
                metadata={
                    'file_path': file_metadata.path,
                    'file_category': base_result.category,
                    'risk_level': base_result.risk_level
                }
            )

            return enhanced_result, confidence_score

        except Exception as e:
            self.logger.error(f"Error analyzing file {file_metadata.path}: {e}")
            # Return safe fallback with low confidence
            fallback_result = FileAnalysisResult(
                path=file_metadata.path,
                deletion_recommendation="keep",
                confidence=ConfidenceLevel.LOW,
                reason="Analysis failed - defaulting to safe action",
                category="unknown",
                risk_level="low",
                suggested_action="manual_review"
            )

            fallback_confidence = ConfidenceScore(
                primary_score=0.1,
                uncertainty=0.3,
                calibration_factor=1.0,
                prediction_type=PredictionType.DELETION_RECOMMENDATION,
                supporting_evidence={'error_fallback': 1.0}
            )

            return fallback_result, fallback_confidence

    def _calculate_confidence_score(
        self,
        file_metadata: FileMetadata,
        analysis_result: FileAnalysisResult,
        include_safety_assessment: bool
    ) -> ConfidenceScore:
        """Calculate comprehensive confidence score for AI prediction."""

        # Base confidence from AI model
        base_confidence = self.confidence_thresholds.get(
            analysis_result.confidence,
            0.5
        )

        # Calculate confidence factors
        factors = {
            'ai_confidence': base_confidence,
            'file_age_confidence': self._calculate_age_confidence(file_metadata),
            'file_extension_confidence': self._calculate_extension_confidence(file_metadata),
            'file_location_confidence': self._calculate_location_confidence(file_metadata),
            'file_size_confidence': self._calculate_size_confidence(file_metadata),
            'pattern_match_confidence': self._calculate_pattern_confidence(file_metadata)
        }

        # Include safety assessment if requested
        if include_safety_assessment:
            try:
                safety_score = self.safety_layer.calculate_safety_score(file_metadata.path)
                factors['safety_alignment'] = safety_score.confidence
            except Exception as e:
                self.logger.warning(f"Safety assessment failed for {file_metadata.path}: {e}")
                factors['safety_alignment'] = 0.5

        # Calculate weighted confidence
        weights = {
            'ai_confidence': 0.4,
            'file_age_confidence': 0.15,
            'file_extension_confidence': 0.15,
            'file_location_confidence': 0.15,
            'file_size_confidence': 0.1,
            'pattern_match_confidence': 0.05
        }

        if 'safety_alignment' in factors:
            weights = {k: v * 0.9 for k, v in weights.items()}
            weights['safety_alignment'] = 0.1

        # Calculate weighted average
        primary_confidence = sum(
            factors[factor] * weight
            for factor, weight in weights.items()
        )

        # Calculate uncertainty based on factor variance
        confidence_values = list(factors.values())
        uncertainty = statistics.stdev(confidence_values) if len(confidence_values) > 1 else 0.1
        uncertainty = min(0.5, uncertainty)  # Cap uncertainty

        # Apply calibration
        calibrated_score = primary_confidence * self.calibration_factor

        # Determine confidence intervals
        confidence_interval_lower = max(0.0, calibrated_score - uncertainty)
        confidence_interval_upper = min(1.0, calibrated_score + uncertainty)

        return ConfidenceScore(
            primary_score=min(1.0, max(0.0, calibrated_score)),
            uncertainty=uncertainty,
            calibration_factor=self.calibration_factor,
            prediction_type=PredictionType.DELETION_RECOMMENDATION,
            supporting_evidence=factors,
            confidence_intervals={
                '95%': (confidence_interval_lower, confidence_interval_upper),
                '68%': (
                    calibrated_score - uncertainty/2,
                    calibrated_score + uncertainty/2
                )
            },
            historical_accuracy=self._get_historical_accuracy()
        )

    def _calculate_age_confidence(self, file_metadata: FileMetadata) -> float:
        """Calculate confidence based on file age."""
        try:
            modified_date = datetime.fromisoformat(file_metadata.modified_date)
            days_old = (datetime.now() - modified_date).days

            # Older files are more predictable
            if days_old > 365:
                return 0.9
            elif days_old > 90:
                return 0.8
            elif days_old > 30:
                return 0.6
            elif days_old > 7:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5

    def _calculate_extension_confidence(self, file_metadata: FileMetadata) -> float:
        """Calculate confidence based on file extension."""
        extension = file_metadata.extension.lower()

        # High confidence extensions (well-understood patterns)
        high_confidence_ext = {
            '.tmp', '.temp', '.cache', '.log', '.bak', '.old',
            '.swp', '.swo', '.pyc', '.class', '.o', '.obj',
            '.dmp', '.crash', '.trace'
        }

        # Medium confidence extensions (somewhat predictable)
        medium_confidence_ext = {
            '.txt', '.csv', '.json', '.xml', '.yaml', '.yml',
            '.conf', '.config', '.ini', '.cfg'
        }

        # Low confidence extensions (user content, unpredictable)
        low_confidence_ext = {
            '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ppt',
            '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi',
            '.zip', '.tar', '.gz', '.rar', '.7z'
        }

        if extension in high_confidence_ext:
            return 0.9
        elif extension in medium_confidence_ext:
            return 0.7
        elif extension in low_confidence_ext:
            return 0.4
        else:
            return 0.6  # Default for unknown extensions

    def _calculate_location_confidence(self, file_metadata: FileMetadata) -> float:
        """Calculate confidence based on file location."""
        path = file_metadata.path.lower()
        parent_dir = file_metadata.parent_directory.lower()

        # High confidence locations (temporary/cache directories)
        high_confidence_locations = [
            '/tmp', '/temp', '/var/tmp', '/var/cache', '/var/log',
            'c:\\temp', 'c:\\tmp', 'c:\\windows\\temp',
            'appdata\\local\\temp', 'library\\caches'
        ]

        # Medium confidence locations (system directories)
        medium_confidence_locations = [
            '/usr/lib', '/usr/share', '/var/lib',
            'c:\\programdata', 'c:\\program files',
            'appdata\\roaming', 'library\\application support'
        ]

        # Low confidence locations (user data)
        low_confidence_locations = [
            '/home', '/users', '/documents', '/desktop',
            'c:\\users', 'my documents', 'desktop'
        ]

        for location in high_confidence_locations:
            if location in parent_dir or location in path:
                return 0.9

        for location in medium_confidence_locations:
            if location in parent_dir or location in path:
                return 0.7

        for location in low_confidence_locations:
            if location in parent_dir or location in path:
                return 0.4

        return 0.6  # Default for unknown locations

    def _calculate_size_confidence(self, file_metadata: FileMetadata) -> float:
        """Calculate confidence based on file size."""
        size_bytes = file_metadata.size_bytes

        # Very small files are often predictable
        if size_bytes < 1024:  # < 1KB
            return 0.9
        elif size_bytes < 10240:  # < 10KB
            return 0.8
        elif size_bytes < 1048576:  # < 1MB
            return 0.7
        elif size_bytes < 104857600:  # < 100MB
            return 0.6
        else:
            return 0.4  # Large files are less predictable

    def _calculate_pattern_confidence(self, file_metadata: FileMetadata) -> float:
        """Calculate confidence based on filename patterns."""
        filename = file_metadata.name.lower()

        # High confidence patterns
        high_confidence_patterns = [
            r'^\.~.*',  # Temporary files
            r'^tmp\d*',
            r'^.*\.tmp$',
            r'^.*\.temp$',
            r'^.*~$',
            r'^.*\.\d+$',  # Backup files
            r'^.*\.bak$',
            r'^.*\.old$',
            r'^.*\.cache$',
            r'^.*\.log$',
            r'^.*\d{4}-\d{2}-\d{2}.*'  # Date-stamped files
        ]

        # Medium confidence patterns
        medium_confidence_patterns = [
            r'^.*cache.*$',
            r'^.*temp.*$',
            r'^.*backup.*$',
            r'^.*log.*$',
            r'^.*\d+.*$'
        ]

        for pattern in high_confidence_patterns:
            if re.match(pattern, filename):
                return 0.9

        for pattern in medium_confidence_patterns:
            if re.search(pattern, filename):
                return 0.7

        return 0.5  # Default for no pattern match

    def _enhance_analysis_result(
        self,
        base_result: FileAnalysisResult,
        confidence_score: ConfidenceScore
    ) -> FileAnalysisResult:
        """Enhance analysis result with confidence information."""
        # Map confidence score to confidence level
        calibrated_score = confidence_score.get_calibrated_score()

        if calibrated_score >= 0.95:
            enhanced_confidence = ConfidenceLevel.VERY_HIGH
        elif calibrated_score >= 0.8:
            enhanced_confidence = ConfidenceLevel.HIGH
        elif calibrated_score >= 0.6:
            enhanced_confidence = ConfidenceLevel.MEDIUM
        else:
            enhanced_confidence = ConfidenceLevel.LOW

        # Add confidence information to reason
        confidence_info = (
            f"Confidence: {calibrated_score:.2f} "
            f"(uncertainty: ±{confidence_score.uncertainty:.2f})"
        )
        enhanced_reason = f"{base_result.reason}. {confidence_info}"

        return FileAnalysisResult(
            path=base_result.path,
            deletion_recommendation=base_result.deletion_recommendation,
            confidence=enhanced_confidence,
            reason=enhanced_reason,
            category=base_result.category,
            risk_level=base_result.risk_level,
            suggested_action=base_result.suggested_action
        )

    def _store_prediction(
        self,
        prediction: Any,
        confidence_score: ConfidenceScore,
        prediction_type: PredictionType,
        metadata: Dict[str, Any]
    ):
        """Store prediction for accuracy tracking."""
        prediction_result = PredictionResult(
            prediction=prediction,
            confidence_score=confidence_score,
            prediction_type=prediction_type,
            metadata=metadata
        )

        self.prediction_history.append(prediction_result)
        self.confidence_history.append(confidence_score)

        # Limit history size
        if len(self.prediction_history) > 10000:
            self.prediction_history = self.prediction_history[-5000:]
        if len(self.confidence_history) > 10000:
            self.confidence_history = self.confidence_history[-5000:]

    def _get_historical_accuracy(self) -> Optional[float]:
        """Get historical accuracy for confidence calibration."""
        if len(self.prediction_history) < 10:
            return None

        # Get recent predictions with ground truth
        recent_predictions = [
            p for p in self.prediction_history[-100:]
            if p.is_correct is not None
        ]

        if len(recent_predictions) < 5:
            return None

        accuracy = sum(1 for p in recent_predictions if p.is_correct) / len(recent_predictions)
        return accuracy

    def calibrate_confidence_scores(self, ground_truth_data: List[Dict[str, Any]]):
        """
        Calibrate confidence scores using ground truth data.

        Args:
            ground_truth_data: List of predictions with ground truth labels
        """
        calibration_pairs = []

        for data_point in ground_truth_data:
            predicted_confidence = data_point.get('predicted_confidence', 0.5)
            actual_outcome = data_point.get('actual_outcome', False)

            calibration_pairs.append((predicted_confidence, actual_outcome))

        if len(calibration_pairs) < 10:
            self.logger.warning("Insufficient data for confidence calibration")
            return

        # Calculate calibration factor using reliability diagram approach
        bins = 10
        bin_size = 1.0 / bins
        calibration_factors = []

        for i in range(bins):
            bin_lower = i * bin_size
            bin_upper = (i + 1) * bin_size

            # Get predictions in this bin
            bin_predictions = [
                (conf, outcome) for conf, outcome in calibration_pairs
                if bin_lower <= conf < bin_upper
            ]

            if len(bin_predictions) >= 5:
                avg_confidence = statistics.mean([conf for conf, _ in bin_predictions])
                accuracy = statistics.mean([outcome for _, outcome in bin_predictions])

                if avg_confidence > 0:
                    calibration_factors.append(accuracy / avg_confidence)

        if calibration_factors:
            self.calibration_factor = statistics.mean(calibration_factors)
            self.calibration_factor = max(0.5, min(2.0, self.calibration_factor))  # Clamp

            self.logger.info(f"Updated confidence calibration factor: {self.calibration_factor:.3f}")

    def calculate_accuracy_metrics(self, test_data: List[Dict[str, Any]]) -> AccuracyMetrics:
        """
        Calculate comprehensive accuracy metrics.

        Args:
            test_data: Test data with predictions and ground truth

        Returns:
            AccuracyMetrics object with comprehensive metrics
        """
        if not test_data:
            raise ValueError("Test data cannot be empty")

        # Calculate overall accuracy
        correct_predictions = sum(1 for item in test_data if item.get('is_correct', False))
        overall_accuracy = correct_predictions / len(test_data)

        # Calculate accuracy by prediction type
        accuracy_by_type = {}
        for pred_type in PredictionType:
            type_data = [
                item for item in test_data
                if item.get('prediction_type') == pred_type
            ]
            if type_data:
                type_correct = sum(1 for item in type_data if item.get('is_correct', False))
                accuracy_by_type[pred_type] = type_correct / len(type_data)
            else:
                accuracy_by_type[pred_type] = 0.0

        # Calculate confidence calibration
        confidence_calibration = self._calculate_confidence_calibration(test_data)

        # Build confidence distribution
        confidence_distribution = {'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
        for item in test_data:
            conf = item.get('confidence', 0.5)
            if conf < 0.4:
                confidence_distribution['low'] += 1
            elif conf < 0.7:
                confidence_distribution['medium'] += 1
            elif conf < 0.9:
                confidence_distribution['high'] += 1
            else:
                confidence_distribution['very_high'] += 1

        # Error analysis
        error_analysis = self._analyze_errors(test_data)

        # Calibration curve data
        calibration_curve = self._generate_calibration_curve(test_data)

        # Uncertainty analysis
        uncertainty_analysis = self._analyze_uncertainty(test_data)

        # Recommendation accuracy
        recommendation_accuracy = self._analyze_recommendation_accuracy(test_data)

        return AccuracyMetrics(
            overall_accuracy=overall_accuracy,
            confidence_calibration=confidence_calibration,
            prediction_accuracy_by_type=accuracy_by_type,
            confidence_distribution=confidence_distribution,
            error_analysis=error_analysis,
            calibration_curve_data=calibration_curve,
            uncertainty_analysis=uncertainty_analysis,
            recommendation_accuracy=recommendation_accuracy
        )

    def _calculate_confidence_calibration(self, test_data: List[Dict[str, Any]]) -> float:
        """Calculate confidence calibration score."""
        if len(test_data) < 10:
            return 0.5

        # Calculate Expected Calibration Error (ECE)
        num_bins = 10
        bin_boundaries = [i / num_bins for i in range(num_bins + 1)]

        ece = 0.0
        for i in range(num_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            # Get samples in this bin
            bin_samples = [
                item for item in test_data
                if bin_lower <= item.get('confidence', 0.5) < bin_upper
            ]

            if bin_samples:
                avg_confidence = statistics.mean([
                    item.get('confidence', 0.5) for item in bin_samples
                ])
                accuracy = statistics.mean([
                    item.get('is_correct', False) for item in bin_samples
                ])

                bin_weight = len(bin_samples) / len(test_data)
                ece += bin_weight * abs(avg_confidence - accuracy)

        # Convert to calibration score (higher is better)
        calibration_score = 1.0 - ece
        return max(0.0, min(1.0, calibration_score))

    def _analyze_errors(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze prediction errors."""
        errors = [
            item for item in test_data
            if not item.get('is_correct', False)
        ]

        if not errors:
            return {'error_rate': 0.0, 'error_patterns': []}

        # Error rate
        error_rate = len(errors) / len(test_data)

        # Common error patterns
        error_patterns = {}
        for error in errors:
            category = error.get('category', 'unknown')
            error_patterns[category] = error_patterns.get(category, 0) + 1

        # Confidence analysis for errors
        error_confidences = [error.get('confidence', 0.5) for error in errors]
        avg_error_confidence = statistics.mean(error_confidences) if error_confidences else 0.5

        return {
            'error_rate': error_rate,
            'error_patterns': error_patterns,
            'avg_error_confidence': avg_error_confidence,
            'total_errors': len(errors)
        }

    def _generate_calibration_curve(self, test_data: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """Generate calibration curve data."""
        # Sort by confidence
        sorted_data = sorted(test_data, key=lambda x: x.get('confidence', 0.5))

        curve_data = []
        bin_size = max(1, len(sorted_data) // 20)  # Aim for ~20 points

        for i in range(0, len(sorted_data), bin_size):
            bin_data = sorted_data[i:i + bin_size]
            if bin_data:
                avg_confidence = statistics.mean([
                    item.get('confidence', 0.5) for item in bin_data
                ])
                accuracy = statistics.mean([
                    item.get('is_correct', False) for item in bin_data
                ])
                curve_data.append((avg_confidence, accuracy))

        return curve_data

    def _analyze_uncertainty(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze uncertainty quantification quality."""
        uncertainties = [
            item.get('uncertainty', 0.1) for item in test_data
            if 'uncertainty' in item
        ]

        if not uncertainties:
            return {'mean_uncertainty': 0.1, 'uncertainty_calibration': 0.5}

        mean_uncertainty = statistics.mean(uncertainties)

        # Calculate uncertainty calibration (how well uncertainty predicts errors)
        high_uncertainty_errors = 0
        high_uncertainty_total = 0

        for item in test_data:
            uncertainty = item.get('uncertainty', 0.1)
            if uncertainty > 0.3:  # High uncertainty threshold
                high_uncertainty_total += 1
                if not item.get('is_correct', False):
                    high_uncertainty_errors += 1

        high_uncertainty_error_rate = (
            high_uncertainty_errors / high_uncertainty_total
            if high_uncertainty_total > 0 else 0.5
        )

        # Good uncertainty quantification should have higher error rates for high uncertainty
        uncertainty_calibration = min(1.0, high_uncertainty_error_rate * 2)

        return {
            'mean_uncertainty': mean_uncertainty,
            'uncertainty_calibration': uncertainty_calibration,
            'high_uncertainty_error_rate': high_uncertainty_error_rate
        }

    def _analyze_recommendation_accuracy(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze accuracy of different recommendation types."""
        recommendations = {}

        for item in test_data:
            rec = item.get('recommendation', 'unknown')
            if rec not in recommendations:
                recommendations[rec] = {'correct': 0, 'total': 0}

            recommendations[rec]['total'] += 1
            if item.get('is_correct', False):
                recommendations[rec]['correct'] += 1

        # Calculate accuracy by recommendation type
        accuracy_by_rec = {}
        for rec, counts in recommendations.items():
            if counts['total'] > 0:
                accuracy_by_rec[rec] = counts['correct'] / counts['total']
            else:
                accuracy_by_rec[rec] = 0.0

        return accuracy_by_rec

    def validate_ai_performance(
        self,
        validation_dataset: str,
        generate_report: bool = True
    ) -> AccuracyMetrics:
        """
        Validate AI performance against a test dataset.

        Args:
            validation_dataset: Name of validation dataset to use
            generate_report: Whether to generate a detailed report

        Returns:
            AccuracyMetrics object with validation results
        """
        if validation_dataset not in self.validation_datasets:
            raise ValueError(f"Validation dataset '{validation_dataset}' not found")

        test_data = self.validation_datasets[validation_dataset]

        # Calculate accuracy metrics
        metrics = self.calculate_accuracy_metrics(test_data)

        # Cache metrics
        self.accuracy_cache[validation_dataset] = metrics

        # Generate report if requested
        if generate_report:
            self._generate_accuracy_report(validation_dataset, metrics)

        return metrics

    def _generate_accuracy_report(self, dataset_name: str, metrics: AccuracyMetrics):
        """Generate a detailed accuracy report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"/home/malu/.projects/ai-disk-cleanup/reports/accuracy_report_{dataset_name}_{timestamp}.json"

        report_data = {
            'dataset_name': dataset_name,
            'timestamp': timestamp,
            'summary_score': metrics.get_summary_score(),
            'overall_accuracy': metrics.overall_accuracy,
            'confidence_calibration': metrics.confidence_calibration,
            'prediction_accuracy_by_type': {
                pred_type.value: accuracy
                for pred_type, accuracy in metrics.prediction_accuracy_by_type.items()
            },
            'confidence_distribution': metrics.confidence_distribution,
            'error_analysis': metrics.error_analysis,
            'uncertainty_analysis': metrics.uncertainty_analysis,
            'recommendation_accuracy': metrics.recommendation_accuracy,
            'calibration_curve_data': metrics.calibration_curve_data
        }

        try:
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)

            self.logger.info(f"Accuracy report generated: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to generate accuracy report: {e}")

    def get_model_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of model performance across all validation datasets."""
        if not self.accuracy_cache:
            return {'status': 'No validation data available'}

        summary = {
            'total_datasets': len(self.accuracy_cache),
            'overall_summary_score': 0.0,
            'dataset_scores': {},
            'calibration_factor': self.calibration_factor,
            'total_predictions': len(self.prediction_history),
            'avg_confidence': 0.0,
            'confidence_trend': 'stable'
        }

        # Calculate scores for each dataset
        dataset_scores = []
        for dataset_name, metrics in self.accuracy_cache.items():
            score = metrics.get_summary_score()
            summary['dataset_scores'][dataset_name] = score
            dataset_scores.append(score)

        if dataset_scores:
            summary['overall_summary_score'] = statistics.mean(dataset_scores)

        # Calculate average confidence
        if self.confidence_history:
            summary['avg_confidence'] = statistics.mean([
                conf.get_calibrated_score() for conf in self.confidence_history[-100:]
            ])

        # Analyze confidence trend
        if len(self.confidence_history) >= 50:
            recent_conf = statistics.mean([
                conf.get_calibrated_score() for conf in self.confidence_history[-10:]
            ])
            older_conf = statistics.mean([
                conf.get_calibrated_score() for conf in self.confidence_history[-50:-10]
            ])

            if recent_conf > older_conf + 0.05:
                summary['confidence_trend'] = 'improving'
            elif recent_conf < older_conf - 0.05:
                summary['confidence_trend'] = 'declining'

        return summary

    def load_validation_dataset(self, dataset_name: str, dataset_path: str):
        """Load a validation dataset from file."""
        try:
            with open(dataset_path, 'r') as f:
                dataset = json.load(f)

            self.validation_datasets[dataset_name] = dataset
            self.logger.info(f"Loaded validation dataset '{dataset_name}' with {len(dataset)} samples")
        except Exception as e:
            self.logger.error(f"Failed to load validation dataset '{dataset_name}': {e}")
            raise

    def save_validation_dataset(self, dataset_name: str, dataset_path: str):
        """Save a validation dataset to file."""
        if dataset_name not in self.validation_datasets:
            raise ValueError(f"Validation dataset '{dataset_name}' not found")

        try:
            with open(dataset_path, 'w') as f:
                json.dump(self.validation_datasets[dataset_name], f, indent=2)

            self.logger.info(f"Saved validation dataset '{dataset_name}' to {dataset_path}")
        except Exception as e:
            self.logger.error(f"Failed to save validation dataset '{dataset_name}': {e}")
            raise