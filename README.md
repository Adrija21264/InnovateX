# 🚀 InnovateX – Enhancing Trigger.dev with Firebase/MongoDB Connectors & a Web Dashboard  

## 📌 Overview  
This project extends **Trigger.dev** by solving two major gaps developers face today:  

1. **Lack of auto-generated connectors for internal APIs (like Firebase & MongoDB).**  
2. **No unified dashboard for monitoring, analytics, and collaboration.**  

By tackling these issues, InnovateX makes Trigger.dev **more usable, scalable, and business-friendly**, especially for **startups, indie developers, and student teams**.  

---

## ❗ Problem 1: Missing Firebase/MongoDB Integrations  

### 🔴 Current Issue  
- Trigger.dev currently has **limited or no direct integration** with Firebase or MongoDB.  
- Workflows requiring:  
  - Firestore events (`document added/updated`)  
  - Authentication triggers (`user created`)  
  - Push notifications  
  - Firebase Cloud Functions  
  are **hard to implement**.  

This makes adoption difficult in the **student/startup ecosystem**, where Firebase dominates.  

---

### ✅ Our Solution – Auto-Generated TypeScript Connectors  
- **Auto-generate connectors** for internal APIs like MongoDB + Firebase Firestore.  
- **Schema-driven generation:** Users paste API schema/spec → system generates ready-to-use TypeScript code.  
- **Example connectors implemented:**  
  - **MongoDB Auth events** (`onUserCreated`)  
  - **Firestore Document Added/Updated** (`onDocumentWrite`)  

---

### 🛠️ Tech & Logic Used  
- **Language:** TypeScript  
- **Database:** MongoDB  
- **Approach:**  
  1. Parse API schema.  
  2. Auto-generate strongly typed TypeScript client code.  
  3. Provide mock testing harness for validation.  
  4. Developers instantly use these connectors in workflows.  

---

### 🌟 Business & User Impact  
- **For Startups/Indie Devs:** Lowers barrier to entry, faster integrations.  
- **For Enterprises:** Ensures reliability with strong typing + testable connectors.  
- **For Trigger.dev:** Expands ecosystem → makes it competitive with Zapier, n8n, Airplane.  

---

## ❗ Problem 2: No Unified Dashboard  

### 🔴 Current Issue  
- Without a dashboard, developers face:  
  - **Hard job monitoring:** Can’t easily track success/failure.  
  - **No analytics/metrics:** No visibility into job frequency, latency, or error rate.  
  - **No collaboration:** PMs, Ops, or Managers can’t interact with workflows.  
- Competing platforms (Zapier, n8n, Airplane) all **offer dashboards** → Trigger.dev feels incomplete.  

---

### ✅ Our Solution – Web-Based Dashboard  
A **web-based dashboard** where developers & teams can:  

- 🔎 **Monitor Jobs** – Status: Running / Failed / Success.  
- 📜 **View Logs** – Full execution logs & error messages.  
- 📊 **Analytics** – Job counts, frequency, error rates, latency trends.  
- 👥 **Team-Friendly** – PMs & Ops can interact without touching code.  

---

### 🛠️ Tech & Logic Used  
- **Frontend:** React + TypeScript  
- **Backend:** Node.js + Express  
- **Database:** MongoDB (storing logs, analytics, job metadata)  
- **Implementation Flow:**  
  1. Jobs send execution metadata → stored in MongoDB.  
  2. Dashboard UI queries this data for live updates.  
  3. Analytics computed via aggregation pipelines.  

---

### 🌟 Business & User Impact  
- **For Developers:** Debug & monitor jobs in real-time → saves time.  
- **For Teams:** Non-developers gain visibility → better collaboration.  
- **For Product Growth:** Feature parity with competitors → boosts adoption.  

---

## 🧩 How This Improves Trigger.dev  
✅ Makes Trigger.dev **more attractive for Firebase/MongoDB-heavy teams**.  
✅ Adds **enterprise-level observability** with dashboards.  
✅ **Balances developer experience (DX) & business needs (UX).**  

---

## ⚙️ Tech Stack  
- **Language:** TypeScript  
- **Backend:** Node.js, Express  
- **Database:** MongoDB  
- **Frontend:** React  
- **Other:** Trigger.dev SDK  

---

## 🚀 Getting Started  

```bash
# Clone the repo
git clone https://github.com/Adrija21264/InnovateX.git
cd InnovateX

# Install dependencies
npm install

# Run backend


npm run server

# Run frontend
npm run client
