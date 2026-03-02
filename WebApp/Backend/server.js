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

app.get('/', (req ,res) => 
 {res.send( { message: "Hello World"} )}
);


app.listen(3001, () => console.log("Backend running on http://localhost:3001"));