import express from "express";
import { db } from "./firebase.js";
import { collection, addDoc, serverTimestamp } from "firebase/firestore";


async function testFirebase() {
  try {
    const ref = await addDoc(collection(db, "test_connection"), {
      message: "Hello Firebase!",
      time: serverTimestamp()
    });
    console.log("🔥 Firebase test write OK. Doc ID:", ref.id);
  } catch (err) {
    console.error("❌ Firebase test write FAILED:", err);
  }
}

testFirebase();


const app = express();
app.use(express.json());

app.post("/log-alert", async (req, res) => {
  try {
    await addDoc(collection(db, "alerts"), {
      ...req.body,
      timestamp: serverTimestamp()
    });
    res.send({ status: "ok" });
  } catch (err) {
    console.error(err);
    res.status(500).send("Error writing to Firestore");
  }
});

app.listen(3001, () => console.log("Backend running on http://localhost:3001"));