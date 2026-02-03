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
  const [fileName, setFileName] = useState("");

  // --- PAYMENT HANDLER ---
  const handlePayment = async () => {
    if (!modelUrl) return;

    try {
      // 1. Create Order on Backend
      // We ask for ₹49 (4900 paise)
      const orderUrl = "https://floorplan-api-sjoa.onrender.com/convert"; 
      const { data } = await axios.post(orderUrl, { amount: 4900 });

      // 2. Configure Razorpay Popup
      const options = {
        key: "rzp_live_SBaCxRDBNkWaSr", // <--- PASTE KEY ID HERE
        amount: data.amount,
        currency: data.currency,
        name: "FloorPlan.AI",
        description: "High-Res 3D Model Download",
        order_id: data.id,
        handler: function (response) {
            // 3. ON SUCCESS
            alert(`Payment Successful! ID: ${response.razorpay_payment_id}`);
            // Trigger Download
            window.open(modelUrl, '_blank');
        },
        prefill: {
            name: "Architect User",
            email: "user@example.com",
            contact: "9999999999"
        },
        theme: {
            color: "#4ade80"
        }
      };

      // 3. Open Popup
      const rzp1 = new window.Razorpay(options);
      rzp1.open();

    } catch (error) {
        console.error("Payment Error:", error);
        alert("Payment initialization failed. Check console.");
    }
  };

  // --- UPLOAD HANDLER ---
  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setFileName(file.name);
    const formData = new FormData();
    formData.append("file", file);

    try {
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
    setFileName("");
  };

  return (
    <div className={`app-container ${modelUrl ? 'full-mode' : ''}`}>
      
      {/* SIDEBAR (Hidden in Full Mode) */}
      <div className="brand-strip">
        <div className="vertical-text">FLOORPLAN.AI</div>
      </div>

      <div className="hero-wrapper">
        
        {/* LEFT TEXT (Hidden in Full Mode) */}
        <div className="hero-content">
          <div className="pill-nav">
            <span className="active">Home</span>
            <span>Services</span>
            <span>Projects</span>
            <span>Pricing</span>
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
            {fileName && <div style={{marginTop: '10px', color: '#666', fontSize: '0.8rem'}}>Selected: {fileName}</div>}
          </div>
        </div>

        {/* VISUAL AREA (Right Side -> Expands to Full Screen) */}
        <div className="hero-visual">
          <div className="abstract-bg"></div>
          
          {/* 3D CANVAS */}
          <Canvas shadows camera={{ position: [0, 0, 8], fov: 45 }}>
            <ambientLight intensity={0.5} />
            <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} />
            <Environment preset="city" />

            <Suspense fallback={null}>
              {modelUrl ? (
                // STATE 1: USER'S MODEL (Brighter & Better Angle)
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
               <p style={{fontSize: '0.8rem', color: '#666'}}>This may take up to 60s for the first run</p>
             </div>
          )}

          {/* FLOATING CONTROLS (Only visible in Full Mode) */}
          {modelUrl && (
            <div className="floating-ui">
              <button className="glass-btn" onClick={resetViewer}>← Back</button>
              
              <button 
                className="glass-btn" 
                style={{background: '#4ade80', color: '#000', fontWeight: 'bold'}}
                onClick={handlePayment}
              >
                Buy High-Res (₹49)
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}