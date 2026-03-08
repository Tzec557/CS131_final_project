import express from "express";
import { receiveAlert } from "../controllers/alertsController.js";
import { deviceAuth } from "../middleware/deviceAuth.js";


const router = express.Router();

router.post("/",deviceAuth, receiveAlert);

export default router;