import { db } from "../firebase/admin.js"
import admin from "firebase-admin";
//import { collection, Timestamp, addDoc} from "firebase/firestore";

console.log("Controller reached");

export async function receiveAlert(req, res){
  console.log("Received alert:", req.body);

  try{
  //check object types
    const { device_id, event, timestamp, location } = req.body || {};

    if(!(typeof device_id === "string" &&  device_id.trim().length > 0))
    {
       return res.status(400).json({ error: "device_id is not a string" });
    }
    if(!(typeof event === "string" && event.trim().length > 0))
    {
       return res.status(400).json({ error: "event not a string" });
    }
    if(!(typeof location === "string" && location.trim().length > 0))
    {
      return res.status(400).json({ error: "location is not a string" });
    }
    if(!(typeof timestamp === "number" && timestamp > 0))
    {
      return res.status(400).json({ error: "timestamp not a unix number" });
    }
   //write to db
    await db.collection("Alerts").add({
    Alert_Event: event,
    device_id: device_id,
    location: location ,
    timestamp: admin.firestore.Timestamp.fromMillis(timestamp * 1000),
    });
      
      return res.status(200).json({
        message: "Alert received",
        received: req.body
  });
  }
   catch (err) {
    console.error("Unable to recieve allert Json:", err);
    return res.status(500).json({ error: "badJson retrieval " });
  }

};