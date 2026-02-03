import React, { useState, Suspense, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage, Float, Environment } from '@react-three/drei';
import axios from 'axios';
import { supabase } from './supabaseClient';
import './App.css';

// --- 3D COMPONENT ---
function Model({ url }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

// --- DECORATIVE BLOB ---
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
  // --- STATE ---
  const [modelUrl, setModelUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [user, setUser] = useState(null);

  // --- AUTH LISTENER ---
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  // --- AUTH HANDLERS ---
  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    resetViewer();
  };

  // --- PAYMENT HANDLER ---
  const handlePayment = async () => {
    if (!modelUrl) return;

    try {
      // 1. Create Order
      const orderUrl = "https://floorplan-api-sjoa.onrender.com/create-order"; 
      const { data } = await axios.post(orderUrl, { amount: 4900 });

      // 2. Razorpay Options
      const options = {
        key: "rzp_live_SBaCxRDBNkWaSr", // <--- PASTE KEY ID HERE
        amount: data.amount,
        currency: data.currency,
        name: "FloorPlan.AI",
        description: "High-Res 3D Model Download",
        order_id: data.id,
        handler: function (response) {
            alert(`Payment Successful! ID: ${response.razorpay_payment_id}`);
            window.open(modelUrl, '_blank');
        },
        prefill: {
            name: user?.user_metadata?.full_name || "User",
            email: user?.email || "user@example.com",
            contact: "9999999999"
        },
        theme: {
            color: "#4ade80"
        }
      };

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
    
    // NEW: If user is logged in, send email
    if (user && user.email) {
        formData.append("user_email", user.email);
    }

    try {
      // Make sure this matches your Render URL
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
      
      {/* SIDEBAR */}
      <div className="brand-strip">
        <div className="vertical-text">FLOORPLAN.AI</div>
      </div>

      <div className="hero-wrapper">
        
        {/* LEFT TEXT */}
        <div className="hero-content">
          
          <div className="pill-nav">
            <span className="active">Home</span>
            <span>Services</span>
            <span>Pricing</span>
            
            {/* AUTH BUTTONS */}
            {user ? (
              <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '15px'}}>
                <span style={{color: '#4ade80', fontWeight: 'bold'}}>
                  Hi, {user.user_metadata.full_name?.split(' ')[0]}
                </span>
                <span onClick={handleLogout} style={{cursor: 'pointer', color: '#666'}}>
                  Logout
                </span>
              </div>
            ) : (
              <span 
                onClick={handleLogin} 
                style={{marginLeft: 'auto', color: '#fff', cursor: 'pointer', borderBottom: '1px solid #4ade80'}}
              >
                Login with Google
              </span>
            )}
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

        {/* VISUAL AREA */}
        <div className="hero-visual">
          <div className="abstract-bg"></div>
          
          <Canvas shadows camera={{ position: [0, 0, 8], fov: 45 }}>
            <ambientLight intensity={0.5} />
            <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} />
            <Environment preset="city" />

            <Suspense fallback={null}>
              {modelUrl ? (
                <Stage environment="city" intensity={1} preset="rembrandt" adjustCamera={1.2}>
                  <Model url={modelUrl} />
                </Stage>
              ) : (
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

              {user && (
                 <div style={{
                    display: 'flex', alignItems: 'center', background: 'rgba(0,0,0,0.6)', 
                    padding: '0 15px', borderRadius: '30px', border: '1px solid rgba(255,255,255,0.1)'
                 }}>
                    <span style={{fontSize: '0.8rem', color: '#ccc'}}>
                      Logged in as {user.user_metadata.full_name?.split(' ')[0]}
                    </span>
                 </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}