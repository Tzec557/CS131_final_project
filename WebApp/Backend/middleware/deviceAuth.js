export const deviceAuth = (req, res, next) => {
  const header = req.headers.authorization;
  const expected = process.env.API_SERVICE_TOKEN?.trim();

  if (!header) {
    return res.status(401).json({ error: "Missing Authorization header" });
  }

  const token = header.replace(/Bearer\s+/i, "").trim();

  if (token !== expected) {
    console.log("Token mismatch:", { token, expected });
    return res.status(403).json({ error: "Invalid token" });
  }

  next();
};