
export async function generateMap(data){
    const res = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(data)
    });
    return res.json();
}
