import React, { useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage, Float, Environment } from '@react-three/drei';
import axios from 'axios';
import './App.css';

// --- 3D COMPONENT ---
function Model({ url }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

// --- DECORATIVE BLOB (For the empty state) ---
function AbstractBlob() {
  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <mesh scale={2.5}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial 
          color="#1a1a1a" 
          metalness={0.9} 
          roughness={0.1} 
          envMapIntensity={1}
        />
      </mesh>
    </Float>
  );
}

export default function App() {
  const [modelUrl, setModelUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      // REPLACE WITH YOUR RENDER URL
      const response = await axios.post("https://floorplan-api-sjoa.onrender.com/convert", formData);
      setModelUrl(response.data.url);
    } catch (error) {
      console.error("Error:", error);
      alert("Conversion failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  const resetViewer = () => {
    setModelUrl(null);
    setLoading(false);
  };

  return (
    // Dynamic Class: If model exists, switch to "full-mode"
    <div className={`app-container ${modelUrl ? 'full-mode' : ''}`}>
      
      {/* SIDEBAR (Hidden in Full Mode) */}
      <div className="brand-strip">
        <div className="vertical-text">FLOORPLAN.AI</div>
        {/* Social Icons could go here */}
      </div>

      <div className="hero-wrapper">
        
        {/* LEFT TEXT (Hidden in Full Mode) */}
        <div className="hero-content">
          <div className="pill-nav">
            <span className="active">Home</span>
            <span>Services</span>
            <span>Projects</span>
            <span>About Us</span>
          </div>

          <div className="big-title">
            WE BUILD <br/>
            <span className="highlight">DIGITAL</span> SPACES
          </div>

          <p className="description">
            From 2D sketches to immersive 3D realities. 
            Upload your floor plan and watch our AI craft tailored solutions 
            to drive your architectural success.
          </p>

          <div className="cta-container">
            {/* The Hidden Input Trick */}
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleUpload}
              id="file-upload"
              style={{ display: 'none' }}
              disabled={loading}
            />
            
            <label htmlFor="file-upload" className="cta-button">
              {loading ? "Processing AI..." : "Transform Your Floorplan"}
              <div className="arrow-circle">↗</div>
            </label>
          </div>
        </div>

        {/* VISUAL AREA (Right Side -> Expands to Full Screen) */}
        <div className="hero-visual">
          <div className="abstract-bg"></div>
          
          {/* 3D CANVAS */}
          <Canvas shadows camera={{ position: [0, 0, 8], fov: 45 }}>
            {/* Lighting for the dark theme */}
            <ambientLight intensity={0.5} />
            <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} />
            <Environment preset="city" />

            <Suspense fallback={null}>
              {modelUrl ? (
  // STATE 1: USER'S MODEL
  // preset="rembrandt" gives professional studio lighting
  // intensity={1} makes it bright
  <Stage environment="city" intensity={1} preset="rembrandt" adjustCamera={1.2}>
    <Model url={modelUrl} />
  </Stage>
) : (
  // STATE 2: DECORATIVE BLOB
  <AbstractBlob />
)}
            </Suspense>
            
            <OrbitControls makeDefault autoRotate={!modelUrl} />
          </Canvas>

          {loading && (
             <div className="loader-container">
               <h3>Building your world...</h3>
             </div>
          )}

          {/* FLOATING CONTROLS (Only visible in Full Mode) */}
          {modelUrl && (
            <div className="floating-ui">
              <button className="glass-btn" onClick={resetViewer}>← Back</button>
              <button className="glass-btn">Download .GLB</button>
              <button className="glass-btn" style={{background: '#4ade80', color: '#000'}}>
                Buy High-Res (₹49)
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}