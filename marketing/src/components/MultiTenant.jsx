import React from 'react';
import { motion } from 'framer-motion';
import tenantImg from '../assets/multi-tenant.png';

const MultiTenant = () => {
  return (
    <section id="multi-tenant">
      <div className="container" style={{ display: 'flex', flexDirection: 'row-reverse', alignItems: 'center', gap: '5rem' }}>
        <motion.div 
          style={{ flex: 1 }}
          initial={{ opacity: 0, x: 50 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <img 
            src={tenantImg} 
            alt="Multi-Tenant Visual" 
            style={{ width: '100%', borderRadius: '32px' }}
          />
        </motion.div>

        <motion.div 
          style={{ flex: 1 }}
          initial={{ opacity: 0, x: -50 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <div className="grad-text" style={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '1rem' }}>
            Built for MSPs
          </div>
          <h2 style={{ textAlign: 'left', marginBottom: '1.5rem' }}>Scale Your <span className="grad-text">Security</span> Operations</h2>
          <p style={{ marginBottom: '2rem' }}>
            SpecterDefence was built from the ground up for multi-tenant scalability. Manage hundreds of tenants with ease, using a unified rules engine and global alerting.
          </p>
          <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '1rem' }}>
             <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent-cyan)' }}>Zero-Touch Onboarding</h4>
             <p style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Connect new tenants in minutes using secure Azure AD App Registrations and OAuth 2.0 flow.</p>
          </div>
          <div className="glass-card" style={{ padding: '1.5rem' }}>
             <h4 style={{ marginBottom: '0.5rem', color: 'var(--accent-cyan)' }}>Global Alert Consolidation</h4>
             <p style={{ fontSize: '1rem', color: 'var(--text-main)' }}>Deduplicated, high-fidelity alerts streamed across all tenants to your central SOC team.</p>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default MultiTenant;
