import React from 'react';
import { motion } from 'framer-motion';
import endpointImg from '../assets/endpoint.png';

const EndpointAgent = () => {
  return (
    <section id="endpoint" style={{ background: 'var(--bg-lighter)' }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', gap: '5rem' }}>
        <motion.div 
          style={{ flex: 1 }}
          initial={{ opacity: 0, x: -50 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <img 
            src={endpointImg} 
            alt="Endpoint Agent Visual" 
            style={{ width: '100%', borderRadius: '32px', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}
          />
        </motion.div>

        <motion.div 
          style={{ flex: 1 }}
          initial={{ opacity: 0, x: 50 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <div className="grad-text" style={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '1rem' }}>
            Deeper Visibility
          </div>
          <h2 style={{ textAlign: 'left', marginBottom: '1.5rem' }}>Native <span className="grad-text">Endpoint</span> Intelligence</h2>
          <p style={{ marginBottom: '2rem' }}>
            The optional Windows-based agent tracks device health, heartbeats, and suspicious process executions like PowerShell abuse and LOLBins—without requiring a kernel driver.
          </p>
          <ul style={{ listStyle: 'none', space: '1rem', color: 'var(--text-main)' }}>
            {[
              "Process Creation Tracking (Event 4688)",
              "De-obfuscated PowerShell Monitoring",
              "New Service Installation Detection",
              "SQLite Local Buffering for Reliability"
            ].map((item, i) => (
              <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-cyan)' }}></div>
                {item}
              </li>
            ))}
          </ul>
        </motion.div>
      </div>
    </section>
  );
};

export default EndpointAgent;
