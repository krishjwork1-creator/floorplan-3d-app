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
  const [projects, setProjects] = useState([]); // <--- NEW: Store user projects

  // --- AUTH LISTENER & PROJECT FETCHING ---
  useEffect(() => {
    // Check active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) fetchProjects(session.user.email); // <--- Fetch on load
    });

    // Listen for login/logout
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProjects(session.user.email); // <--- Fetch on login
      } else {
        setProjects([]); // Clear on logout
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // --- FETCH PROJECTS FUNCTION ---
  const fetchProjects = async (email) => {
    try {
      const { data, error } = await supabase
        .from('user_projects')
        .select('*')
        .eq('user_email', email)
        .order('created_at', { ascending: false }); // Newest first
      
      if (error) throw error;
      setProjects(data || []);
    } catch (error) {
      console.error("Error fetching projects:", error);
    }
  };

  // --- AUTH HANDLERS ---
  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({ provider: 'google' });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    resetViewer();
  };

  // --- PAYMENT HANDLER ---
  const handlePayment = async () => {
    if (!modelUrl) return;

    try {
      const orderUrl = "https://floorplan-api-sjoa.onrender.com/create-order"; 
      const { data } = await axios.post(orderUrl, { amount: 4900 });

      const options = {
        key: "rzp_live_SBaCxRDBNkWaSr", // <--- KEEP YOUR KEY HERE
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
        theme: { color: "#4ade80" }
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
    if (user && user.email) formData.append("user_email", user.email);

    try {
      const response = await axios.post("https://floorplan-api-sjoa.onrender.com/convert", formData);
      setModelUrl(response.data.url);
      if (user) fetchProjects(user.email); // Refresh list after upload
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

  // --- LOAD SAVED PROJECT ---
  const loadProject = (url, name) => {
    setModelUrl(url);
    setFileName(name);
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

          {/* MAIN CTA */}
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
              {loading ? "Processing AI..." : "Transform New Floorplan"}
              <div className="arrow-circle">↗</div>
            </label>
            {fileName && <div style={{marginTop: '10px', color: '#666', fontSize: '0.8rem'}}>Selected: {fileName}</div>}
          </div>

          {/* --- NEW: PROJECT LIBRARY (Visible only if logged in) --- */}
          {user && projects.length > 0 && (
            <div className="project-library" style={{marginTop: '40px'}}>
              <h4 style={{color: '#fff', marginBottom: '15px', borderBottom: '1px solid #333', paddingBottom: '5px'}}>
                YOUR RECENT PROJECTS
              </h4>
              <div style={{display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '200px', overflowY: 'auto'}}>
                {projects.map((proj) => (
                  <div 
                    key={proj.id} 
                    onClick={() => loadProject(proj.model_url, proj.project_name)}
                    style={{
                      background: 'rgba(255,255,255,0.05)', 
                      padding: '10px', 
                      borderRadius: '8px', 
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      transition: '0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                    onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.05)'}
                  >
                    <div style={{width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80', marginRight: '10px'}}></div>
                    <span style={{color: '#ccc', fontSize: '0.9rem'}}>{proj.project_name}</span>
                    <span style={{marginLeft: 'auto', color: '#666', fontSize: '0.7rem'}}>
                      {new Date(proj.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

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
            </div>
          )}

        </div>
      </div>
    </div>
  );
}