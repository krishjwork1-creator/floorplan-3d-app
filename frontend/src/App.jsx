import React, { useState, Suspense, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage, Float, Environment } from '@react-three/drei';
import axios from 'axios';
import { supabase } from './supabaseClient';
import toast, { Toaster } from 'react-hot-toast'; // <--- NEW IMPORT
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
  const [modelUrl, setModelUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [user, setUser] = useState(null);
  const [projects, setProjects] = useState([]);

  // --- AUTH & DATA LOADING ---
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) fetchProjects(session.user.email);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        fetchProjects(session.user.email);
      } else {
        setProjects([]);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProjects = async (email) => {
    try {
      const { data, error } = await supabase
        .from('user_projects')
        .select('*')
        .eq('user_email', email)
        .order('created_at', { ascending: false });
      
      if (error) throw error;
      setProjects(data || []);
    } catch (error) {
      console.error("Error fetching projects:", error);
    }
  };

  // --- ACTIONS ---
  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({ provider: 'google' });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    resetViewer();
    toast.success("Logged out successfully");
  };

  const handleDeleteProject = async (e, id) => {
    e.stopPropagation(); // Stop the click from opening the project
    
    // Optimistic UI Update (Remove it from screen immediately)
    setProjects(projects.filter(p => p.id !== id));
    
    try {
      const { error } = await supabase
        .from('user_projects')
        .delete()
        .eq('id', id);

      if (error) throw error;
      toast.success("Project deleted");
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Could not delete project");
      // Optional: Fetch projects again to revert if failed
    }
  };

  const handlePayment = async () => {
    if (!modelUrl) return;
    const toastId = toast.loading("Initializing payment...");

    try {
      const orderUrl = "https://floorplan-api-sjoa.onrender.com/create-order"; 
      const { data } = await axios.post(orderUrl, { amount: 4900 });
      toast.dismiss(toastId);

      const options = {
        key: "rzp_live_SBaCxRDBNkWaSr", 
        amount: data.amount,
        currency: data.currency,
        name: "FloorPlan.AI",
        description: "High-Res 3D Model Download",
        order_id: data.id,
        handler: function (response) {
            toast.success(`Payment Successful! ID: ${response.razorpay_payment_id}`);
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
        toast.dismiss(toastId);
        toast.error("Payment failed to start");
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setFileName(file.name);
    const toastId = toast.loading("Processing Floorplan... (This takes 60s)");
    
    const formData = new FormData();
    formData.append("file", file);
    if (user && user.email) formData.append("user_email", user.email);

    try {
      const response = await axios.post("https://floorplan-api-sjoa.onrender.com/convert", formData);
      
      toast.dismiss(toastId);
      toast.success("Conversion Complete!");
      
      setModelUrl(response.data.url);
      if (user) fetchProjects(user.email); 
    } catch (error) {
      console.error("Error:", error);
      toast.dismiss(toastId);
      toast.error("Conversion failed. Check server logs.");
    } finally {
      setLoading(false);
    }
  };

  const resetViewer = () => {
    setModelUrl(null);
    setLoading(false);
    setFileName("");
  };

  const loadProject = (url, name) => {
    setModelUrl(url);
    setFileName(name);
    toast.success(`Loaded ${name}`);
  };

  return (
    <div className={`app-container ${modelUrl ? 'full-mode' : ''}`}>
      <Toaster position="top-center" reverseOrder={false} /> {/* <--- NOTIFICATION HUB */}
      
      <div className="brand-strip">
        <div className="vertical-text">FLOORPLAN.AI</div>
      </div>

      <div className="hero-wrapper">
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
                <span onClick={handleLogout} style={{cursor: 'pointer', color: '#666', fontSize: '0.9rem'}}>
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
              {loading ? "AI Processing..." : "Transform New Floorplan"}
              <div className="arrow-circle">↗</div>
            </label>
            {fileName && <div style={{marginTop: '10px', color: '#666', fontSize: '0.8rem'}}>Selected: {fileName}</div>}
          </div>

          {/* PROJECT LIBRARY */}
          {user && projects.length > 0 && (
            <div className="project-library" style={{marginTop: '40px'}}>
              <h4 style={{color: '#fff', marginBottom: '15px', borderBottom: '1px solid #333', paddingBottom: '5px', fontSize: '0.9rem', letterSpacing: '1px'}}>
                YOUR PROJECTS
              </h4>
              <div style={{display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '250px', overflowY: 'auto', paddingRight: '5px'}}>
                {projects.map((proj) => (
                  <div 
                    key={proj.id} 
                    onClick={() => loadProject(proj.model_url, proj.project_name)}
                    className="project-card" // Added class for hover effects
                    style={{
                      background: 'rgba(255,255,255,0.03)', 
                      padding: '12px', 
                      borderRadius: '8px', 
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      border: '1px solid transparent',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                      e.currentTarget.style.borderColor = 'rgba(74, 222, 128, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                      e.currentTarget.style.borderColor = 'transparent';
                    }}
                  >
                    <div style={{width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80', marginRight: '12px'}}></div>
                    
                    <div style={{display: 'flex', flexDirection: 'column'}}>
                      <span style={{color: '#e0e0e0', fontSize: '0.85rem', fontWeight: '500'}}>
                        {proj.project_name.length > 20 ? proj.project_name.substring(0, 18) + '...' : proj.project_name}
                      </span>
                      <span style={{color: '#666', fontSize: '0.7rem'}}>
                        {new Date(proj.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    {/* DELETE BUTTON */}
                    <button 
                      onClick={(e) => handleDeleteProject(e, proj.id)}
                      style={{
                        marginLeft: 'auto', 
                        background: 'transparent', 
                        border: 'none', 
                        color: '#666', 
                        cursor: 'pointer',
                        padding: '5px',
                        borderRadius: '4px'
                      }}
                      onMouseEnter={(e) => {e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}}
                      onMouseLeave={(e) => {e.currentTarget.style.color = '#666'; e.currentTarget.style.background = 'transparent'}}
                      title="Delete Project"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

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