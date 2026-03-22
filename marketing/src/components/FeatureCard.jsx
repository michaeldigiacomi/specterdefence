import React from 'react';
import { motion } from 'framer-motion';

const FeatureCard = ({ icon: Icon, title, description, delay = 0 }) => {
  return (
    <motion.div 
      className="glass glass-card"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay }}
    >
      <div className="flex-center grad-bg" style={{ 
        width: '56px', 
        height: '56px', 
        borderRadius: '16px', 
        marginBottom: '1.5rem',
        color: 'white'
      }}>
        <Icon size={28} />
      </div>
      <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem', fontWeight: 700 }}>{title}</h3>
      <p>{description}</p>
    </motion.div>
  );
};

export default FeatureCard;
