"""
Demo script showing how UEBA can be integrated with existing SpecterDefence monitoring.

This demonstrates the ML/UEBA capabilities that were added to the platform.
"""

import numpy as np
from datetime import datetime, timedelta
import time

# This would typically be imported from the actual ueba module
# For demonstration purposes, we'll show the concepts


def demonstrate_ueba_integration():
    """
    Demonstrate how UEBA system integrates with existing monitoring.
    
    The UEBA system:
    1. Processes behavioral data from various security sources
    2. Builds user behavior models using ML techniques
    3. Detects anomalies and calculates risk scores
    4. Integrates with alerting system for automated responses
    """
    
    print("=== SpecterDefence UEBA Integration Demo ===")
    
    # Example of behavioral data that can be processed
    example_user_data = {
        "user_id": "user-123",
        "login_times": [
            datetime.now() - timedelta(hours=2),
            datetime.now() - timedelta(hours=8), 
            datetime.now() - timedelta(days=1),
            datetime.now() - timedelta(days=2)
        ],
        "locations": [
            (40.7128, -74.0060),  # New York
            (34.0522, -118.2437), # Los Angeles  
            (51.5074, -0.1278),   # London
        ],
        "failed_logins": 3,
        "email_count": 45,
    }
    
    print("\nExample user behavior data:")
    for key, value in example_user_data.items():
        print(f"  {key}: {value}")
    
    # Example anomaly detection result (would come from actual UEBA system)
    print("\n=== UEBA Anomaly Detection Result ===")
    anomaly_result = {
        "user_id": "user-123",
        "anomaly_scores": [-0.85, -0.62, 0.21, -0.91],
        "anomaly_labels": [-1, -1, 1, -1],  # -1 = anomaly, 1 = normal
        "risk_score": 0.75,
        "timestamp": datetime.now().isoformat(),
        "anomalies_detected": 3
    }
    
    print(f"Risk Score: {anomaly_result['risk_score']:.2f}")
    print(f"Anomalies Detected: {anomaly_result['anomalies_detected']}")
    print("Anomaly labels (1=normal, -1=anomalous):", anomaly_result['anomaly_labels'])
    
    # Example of how the system would calculate composite score
    print("\n=== Risk Scoring ===")
    print("The UEBA system calculates a comprehensive risk score combining:")
    print("  • Behavioral anomaly detection (70%)")
    print("  • Login time irregularity (30%)") 
    print("  • Geographic travel patterns (40%)")
    print("  • Authentication factors (30%)")
    
    # Example of alert generation
    print("\n=== Alert Generation ===")
    if anomaly_result['risk_score'] > 0.7:
        print("⚠️  HIGH RISK ALERT: User 'user-123' shows suspicious behavior")
        print("   - Detected multiple geographically distant logins")
        print("   - Unusual login time patterns")
        print("   - Elevated failed login attempts")
        print("   - Automated remediation triggered (if enabled)")
    elif anomaly_result['risk_score'] > 0.5:
        print("⚠️  MEDIUM RISK: User 'user-123' behavior deviation detected")
        print("   - Review user access patterns")
        print("   - Consider additional verification")
    else:
        print("✅ LOW RISK: Normal behavior patterns detected")


if __name__ == "__main__":
    demonstrate_ueba_integration()