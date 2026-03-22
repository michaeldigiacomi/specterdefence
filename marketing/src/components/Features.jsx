import React from 'react';
import FeatureCard from './FeatureCard';
import { Users, AlertTriangle, Search, Activity, Lock, Globe } from 'lucide-react';

const Features = () => {
  const features = [
    {
      icon: Users,
      title: "Multi-Tenant Management",
      description: "Monitor dozens of M365 tenants from a single pane of glass. Perfect for MSPs and large enterprises."
    },
    {
      icon: Activity,
      title: "MFA Compliance Tracking",
      description: "Continuously analyze MFA strength (FIDO2 vs SMS) and enrollment status across all users."
    },
    {
      icon: AlertTriangle,
      title: "Real-Time Threat Detection",
      description: "Detect impossible travel, brute-force attempts, and login anomalies in seconds."
    },
    {
      icon: Search,
      title: "Insider Threat & DLP",
      description: "Monitor SharePoint sharing events and sensitive data exposure to prevent exfiltration."
    },
    {
      icon: Lock,
      title: "Active Policy Monitoring",
      description: "Track Conditional Access policy changes and detect security drift automatically."
    },
    {
      icon: Globe,
      title: "Global Visualization",
      description: "Interactive map visualizing login activity and security threats across the globe."
    }
  ];

  return (
    <section id="features">
      <div className="container">
        <h2>Unmatched <span className="grad-text">Visibility</span> & Control</h2>
        <div className="grid-cols-3">
          {features.map((f, i) => (
            <FeatureCard key={i} {...f} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
