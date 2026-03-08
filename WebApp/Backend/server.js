import express from "express";
import cors from "cors"
import alertsRouter from "./routes/alerts.js";
import dotenv from "dotenv";
//import  {app, auth , db } from "firebase"
dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

app.use("/alerts", alertsRouter);

const PORT = 3001;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Server running on port ${PORT}`);
});
