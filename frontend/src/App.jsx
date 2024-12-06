import React, { useState } from "react";

function App() {
  const [points, setPoints] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSimulate = async () => {
    setError(null);
    setResult(null);
    if (!points || isNaN(points)) {
      setError("Please enter a valid number");
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/position?points=${points}`);
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Error from server");
      }
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "50px" }}>
      <h1>Padel Ranking Position Simulator</h1>
      <input 
        type="number" 
        placeholder="Enter your points" 
        value={points} 
        onChange={(e) => setPoints(e.target.value)} 
        style={{ padding: "10px", fontSize: "1em", marginBottom: "10px" }}
      />
      <button onClick={handleSimulate} style={{ padding: "10px 20px", fontSize: "1em", cursor: "pointer" }}>
        Simulate Position
      </button>
      {error && <p style={{ color: "red", marginTop: "20px" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: "20px" }}>
          <p>Your future position is: <strong>{result.position}</strong></p>
          <p>You need <strong>{result.additional_points_needed}</strong> additional point(s)</p>
        </div>
      )}
    </div>
  );
}

export default App;
