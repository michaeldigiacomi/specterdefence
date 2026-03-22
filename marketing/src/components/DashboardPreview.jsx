import React from 'react';
import { motion } from 'framer-motion';
import dashboardImg from '../assets/dashboard.png';

const DashboardPreview = () => {
  return (
    <section id="dashboard">
      <div className="container" style={{ textAlign: 'center' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1 }}
        >
          <div className="grad-text" style={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '1rem' }}>
            Unified Control Plane
          </div>
          <h2 style={{ marginBottom: '1.5rem' }}>One Pane of <span className="grad-text">Glass</span></h2>
          <p style={{ maxWidth: '700px', margin: '0 auto 4rem' }}>
            A comprehensive overview of your security posture across all tenants. Real-time maps, audit logs, and risk assessments—all in one place.
          </p>
          
          <div className="grad-border" style={{ padding: '4px', borderRadius: '24px', maxWidth: '1000px', margin: '0 auto', boxShadow: '0 30px 60px rgba(0,0,0,0.6)' }}>
            <img 
              src={dashboardImg} 
              alt="SpecterDefence Dashboard" 
              style={{ width: '100%', borderRadius: '20px', display: 'block' }}
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default DashboardPreview;
