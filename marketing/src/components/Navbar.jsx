import React from 'react';
import { Shield } from 'lucide-react';

const Navbar = () => {
  return (
    <nav className="glass" style={{
      position: 'fixed',
      top: '1.5rem',
      left: '50%',
      transform: 'translateX(-50%)',
      width: 'max-content',
      minWidth: '600px',
      borderRadius: '999px',
      padding: '0.75rem 2rem',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '4rem'
    }}>
      <div className="flex-center" style={{ gap: '0.75rem' }}>
        <Shield className="grad-text" size={28} style={{ color: 'var(--accent-cyan)' }} />
        <span style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.5px' }}>
          Specter<span className="grad-text">Defence</span>
        </span>
      </div>
      
      <div style={{ display: 'flex', gap: '2rem', fontWeight: 500, color: 'var(--text-muted)' }}>
        <a href="#features" className="hover-white">Features</a>
        <a href="#endpoint" className="hover-white">Endpoint</a>
        <a href="#docs" className="hover-white">Docs</a>
        <a href="#pricing" className="hover-white">Pricing</a>
      </div>

      <button className="btn-primary" style={{ padding: '0.6rem 1.5rem', borderRadius: '999px' }}>
        Get Started
      </button>
      
      <style>{`
        .hover-white:hover { color: white; }
      `}</style>
    </nav>
  );
};

export default Navbar;
