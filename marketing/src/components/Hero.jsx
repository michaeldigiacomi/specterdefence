import React from 'react';
import { motion } from 'framer-motion';
import heroImg from '../assets/hero.png';

const Hero = () => {
  return (
    <section id="hero" style={{ paddingTop: '12rem', paddingBottom: '6rem' }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', gap: '4rem' }}>
        <div style={{ flex: 1 }}>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="glass glass-pill" style={{ display: 'inline-block', marginBottom: '1.5rem', border: '1px solid var(--accent-cyan)', color: 'var(--accent-cyan)', fontSize: '0.9rem', fontWeight: 600 }}>
              v1.1.0 Now Available
            </div>
            <h1>
              Secure Your <span className="grad-text">Microsoft 365</span>. Period.
            </h1>
            <p style={{ fontSize: '1.25rem', marginBottom: '3rem', maxWidth: '540px' }}>
              Automated security posture monitoring, real-time threat detection, and continuous management—built natively for speed and multi-tenant scale.
            </p>
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <button className="btn-primary grad-bg" style={{ color: 'white' }}>Start for Free</button>
              <button className="btn-outline">View Documentation</button>
            </div>
          </motion.div>
        </div>

        <motion.div 
          style={{ flex: 1, position: 'relative' }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
        >
          <div className="grad-border" style={{ padding: '2px', borderRadius: '40px' }}>
             <img 
              src={heroImg} 
              alt="SpecterDefence Visual" 
              style={{ width: '100%', borderRadius: '38px', display: 'block' }}
            />
          </div>
          {/* Subtle Glow Background */}
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: '120%',
            height: '120%',
            background: 'radial-gradient(circle, rgba(0,242,254,0.1) 0%, transparent 70%)',
            transform: 'translate(-50%, -50%)',
            zIndex: -1
          }}></div>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;
