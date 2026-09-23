"""
Tests for UEBA (User and Entity Behavior Analytics) module.
"""

import numpy as np
import pytest
from datetime import datetime, timedelta

# Test the UEBA components that were added
def test_behavior_model_creation():
    """Test that behavior model can be created."""
    from src.ueba.behavior_model import BehaviorModel
    
    # Create a simple model for testing
    model = BehaviorModel(window_size=10)
    
    # Check initialization
    assert hasattr(model, 'window_size')
    assert hasattr(model, 'is_trained')
    assert model.window_size == 10
    assert not model.is_trained

def test_anomaly_detector_creation():
    """Test that anomaly detector can be created."""
    from src.ueba.anomaly_detector import AnomalyDetector
    
    # Create a detector
    detector = AnomalyDetector()
    
    # Check initialization
    assert hasattr(detector, 'behavior_models')
    assert hasattr(detector, 'risk_scores')
    assert len(detector.behavior_models) == 0

def test_user_risk_scorer_creation():
    """Test that user risk scorer can be created."""
    from src.ueba.user_risk_scoring import UserRiskScorer
    
    # Create a scorer
    scorer = UserRiskScorer(decay_factor=0.9, max_age_hours=24)
    
    # Check initialization
    assert hasattr(scorer, 'decay_factor')
    assert hasattr(scorer, 'max_age_hours')
    assert hasattr(scorer, 'user_scores')
    assert hasattr(scorer, 'current_scores')

def test_feature_vector_creation():
    """Test that feature vectors can be created from behavior data."""
    from src.ueba.integration import UEBAIntegration
    
    # Create integration instance
    integration = UEBAIntegration()
    
    # Test with sample behavior data
    sample_data = {
        "login_times": [
            datetime.now() - timedelta(hours=2),
            datetime.now() - timedelta(hours=8), 
            datetime.now() - timedelta(days=1)
        ],
        "locations": [
            (40.7128, -74.0060),
            (34.0522, -118.2437),
        ],
        "failed_logins": 2,
        "email_count": 12
    }
    
    # This would create a feature vector
    features = integration._create_feature_vector(sample_data)
    assert isinstance(features, np.ndarray)
    assert len(features.shape) == 2  # Should be 2D array (n_samples, n_features)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])