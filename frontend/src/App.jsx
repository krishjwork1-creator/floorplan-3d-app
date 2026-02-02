import React, { useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage, Grid } from '@react-three/drei';
import axios from 'axios';
import './App.css';

// --- 3D MODEL COMPONENT ---
function Model({ url }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

export default function App() {
  const [modelUrl, setModelUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState("");

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setFileName(file.name);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      // REPLACE THIS URL WITH YOUR RENDER URL
      const response = await axios.post("https://floorplan-api-sjoa.onrender.com/convert", formData);
      setModelUrl(response.data.url);
    } catch (error) {
      console.error("Error:", error);
      alert("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      
      {/* NAVBAR */}
      <nav className="navbar">
        <div className="logo">FLOORPLAN<span style={{color: '#3b82f6'}}>.AI</span></div>
        <div className="nav-links">
          <button>Pricing</button>
          <button>Login</button>
          <button className="btn-primary">Get Pro</button>
        </div>
      </nav>

      {/* MAIN CONTENT SPLIT */}
      <div className="main-content">
        
        {/* LEFT PANEL: CONTROLS */}
        <div className="sidebar">
          <div className="hero-text">
            <h1>2D to 3D.<br/>Instantly.</h1>
            <p>Upload any floor plan image and let our AI engine build a 3D digital twin in seconds.</p>
          </div>

          <div className="upload-zone">
            <span className="icon-upload">📂</span>
            <p>
              {loading ? "Processing..." : "Drag & drop or click to upload"}
            </p>
            <span style={{fontSize: '0.8rem', color: '#666'}}>
              {fileName ? `Selected: ${fileName}` : "Supports JPG, PNG"}
            </span>
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleUpload} 
              disabled={loading}
            />
          </div>

          <div style={{marginTop: 'auto', fontSize: '0.8rem', color: '#555'}}>
            © 2026 Floorplan.AI • v1.0
          </div>
        </div>

        {/* RIGHT PANEL: 3D VIEWER */}
        <div className="viewer-area">
          <Canvas shadows camera={{ position: [0, 50, 50], fov: 45 }}>
            <color attach="background" args={['#101010']} />
            
            {/* Tech Grid Floor */}
            <Grid infiniteGrid fadeDistance={50} cellColor="#333" sectionColor="#555" />
            
            <OrbitControls makeDefault autoRotate={!modelUrl} autoRotateSpeed={0.5} />
            
            <Suspense fallback={null}>
              <Stage environment="city" intensity={0.5} contactShadow={false}>
                {modelUrl && <Model url={modelUrl} />}
              </Stage>
            </Suspense>
          </Canvas>

          {/* LOADING STATE OVERLAY */}
          {loading && (
            <div className="loading-overlay">
              <div className="spinner"></div>
              <span>Building Geometry...</span>
            </div>
          )}

          {/* INSTRUCTIONS OVERLAY (If no model yet) */}
          {!modelUrl && !loading && (
            <div style={{
              position: 'absolute', bottom: '20px', right: '20px', 
              color: '#555', fontSize: '0.8rem'
            }}>
              Waiting for input...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}