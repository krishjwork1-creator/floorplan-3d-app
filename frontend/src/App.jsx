import React, { useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Stage, Html } from '@react-three/drei';
import axios from 'axios';
import './App.css'; // We will use the default CSS for now

// A component to load the 3D Model
function Model({ url }) {
  // useGLTF loads the file from the URL
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

// A Loading bar component
function Loader() {
  return <Html center>Converting... Please wait.</Html>;
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
      // 1. Send to Backend
      // Note: We removed "responseType: blob" because we expect JSON now
      const response = await axios.post("http://127.0.0.1:8000/convert", formData);

      // 2. The backend now returns { "url": "https://..." }
      const publicUrl = response.data.url;
      console.log("Model available at:", publicUrl);
      
      setModelUrl(publicUrl);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Conversion failed. Check console.");
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      
      {/* Header / Upload Bar */}
      <div style={{ padding: "20px", background: "#333", color: "white", display: "flex", gap: "20px", alignItems: "center" }}>
        <h2>FloorPlan 3D</h2>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleUpload} 
          style={{ color: "white" }}
        />
      </div>

      {/* 3D Canvas Area */}
      <div style={{ flex: 1, background: "#f0f0f0" }}>
        <Canvas shadows camera={{ position: [0, 50, 50], fov: 50 }}>
          {/* Controls: Let user rotate/zoom */}
          <OrbitControls makeDefault />
          
          <Suspense fallback={<Loader />}>
            {/* Stage: Automatically adds lighting and centers the model */}
            <Stage environment="city" intensity={0.6}>
              {modelUrl && <Model url={modelUrl} />}
            </Stage>
          </Suspense>
          
        </Canvas>
        
        {loading && (
            <div style={{
                position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
                background: "white", padding: "20px", borderRadius: "10px", boxShadow: "0 0 10px rgba(0,0,0,0.2)"
            }}>
                Processing your floorplan...
            </div>
        )}
      </div>
    </div>
  );
}