"""
Behavior Model for User and Entity Behavior Analytics.

This module implements machine learning models to establish baseline behavior patterns
for users and entities within Microsoft 365 environments.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class BehaviorModel:
    """Behavior model for establishing baseline user/entity patterns."""

    def __init__(self, window_size: int = 30):
        """
        Initialize the behavior model.
        
        Args:
            window_size: Number of historical data points to consider for baseline
        """
        self.window_size = window_size
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # Retain 95% of variance
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
        self.baseline_features = None
        
    def fit(self, features: np.ndarray) -> None:
        """
        Fit the behavior model on historical feature data.
        
        Args:
            features: Array of feature vectors representing user/entity behavior
        """
        logger.info("Fitting behavior model with %d samples", len(features))
        
        # Standardize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Apply PCA for dimensionality reduction
        features_pca = self.pca.fit_transform(features_scaled)
        
        # Train isolation forest model
        self.model.fit(features_pca)
        
        self.is_trained = True
        logger.info("Behavior model trained successfully")
        
    def predict_anomaly(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict anomalies in the given feature set.
        
        Args:
            features: Array of feature vectors to analyze
            
        Returns:
            Tuple of (anomaly_scores, anomaly_labels)
        """
        if not self.is_trained:
            raise RuntimeError("Behavior model must be trained before making predictions")
            
        # Transform features using fitted scaler and PCA
        features_scaled = self.scaler.transform(features)
        features_pca = self.pca.transform(features_scaled)
        
        # Get anomaly scores (lower is more anomalous)
        anomaly_scores = self.model.decision_function(features_pca)
        
        # Get binary anomaly labels (1 = normal, -1 = anomaly)
        anomaly_labels = self.model.predict(features_pca)
        
        return anomaly_scores, anomaly_labels
        
    def get_feature_importance(self) -> np.ndarray:
        """
        Get feature importance from the PCA model.
        
        Returns:
            Array of feature importances
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained first")
            
        # For PCA, we can use the explained variance ratio for each component
        return self.pca.explained_variance_ratio_