import os
import json
import csv

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "historical"))

def generate_datasets():
    os.makedirs(os.path.join(DATA_DIR, "fir"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "cdr"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "financial"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "surveillance"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "criminal_history"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "intelligence"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "vehicles"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "social"), exist_ok=True)

    # 1. FIRs (20 FIRs across 5 historical cases)
    firs = [
        # CASE-101: Operation Shadow Net (Cyber-fraud & logistics module in Chennai)
        {"fir_no": "FIR-101-01", "case_id": "case-101", "police_station": "Central Station PS", "date": "2026-08-01T10:00:00", "suspects": [{"name": "Ravi Kumar", "role": "primary_target", "phone": "9876543210", "vehicle": "TN01AB1234"}, {"name": "Arun", "role": "logistics_driver"}], "complaint_text": "Primary suspect Ravi Kumar spotted meeting associate Arun at Central Station. Target observed driving white Swift TN01AB1234 and coordinating via contact 9876543210."},
        {"fir_no": "FIR-101-02", "case_id": "case-101", "police_station": "Anna Nagar PS", "date": "2026-08-03T14:30:00", "suspects": [{"name": "Vikram Seth", "role": "tech_operator", "phone": "9876543212"}, {"name": "Karthik Raj", "role": "mule_recruiter"}], "complaint_text": "Phishing and OTP rerouting module operated by Vikram Seth in coordination with mule handler Karthik Raj."},
        {"fir_no": "FIR-101-03", "case_id": "case-101", "police_station": "T Nagar PS", "date": "2026-08-05T16:00:00", "suspects": [{"name": "Deepak Verma", "role": "cashier", "phone": "9876543214"}], "complaint_text": "Suspicious ATM withdrawal runs executed by Deepak Verma under instructions from senior handler."},
        {"fir_no": "FIR-101-04", "case_id": "case-101", "police_station": "Central Station PS", "date": "2026-08-08T11:20:00", "suspects": [{"name": "Ravi Kumar", "role": "coordinator"}, {"name": "Suresh Nair", "role": "hardware_supplier"}], "complaint_text": "Ravi Kumar purchased 50 pre-activated SIM cards from hardware merchant Suresh Nair."},
        
        # CASE-203: Port Smuggling & Container Diversion
        {"fir_no": "FIR-203-01", "case_id": "case-203", "police_station": "Harbour PS", "date": "2026-06-10T09:15:00", "suspects": [{"name": "Ravi K", "role": "customs_broker", "vehicle": "TN01AB1234"}, {"name": "Manish Shah", "role": "importer"}], "complaint_text": "Customs broker Ravi K cleared unauthorized consignment at Harbour Gate 4. Vehicle TN01AB1234 sighted on CCTV."},
        {"fir_no": "FIR-203-02", "case_id": "case-203", "police_station": "Royapuram PS", "date": "2026-06-15T18:45:00", "suspects": [{"name": "Prakash Rao", "role": "dock_supervisor"}, {"name": "Salim Khan", "role": "freight_operator"}], "complaint_text": "Dock supervisor Prakash Rao falsified manifest records for freight operator Salim Khan."},
        {"fir_no": "FIR-203-03", "case_id": "case-203", "police_station": "Harbour PS", "date": "2026-06-22T12:00:00", "suspects": [{"name": "Anand Mohan", "role": "warehouse_owner"}], "complaint_text": "Undocumented electronic parts stored at North Wharf Warehouse managed by Anand Mohan."},
        {"fir_no": "FIR-203-04", "case_id": "case-203", "police_station": "Royapuram PS", "date": "2026-07-02T15:30:00", "suspects": [{"name": "Ravi K", "role": "broker"}, {"name": "Tariq Ahmed", "role": "financer"}], "complaint_text": "Meeting between Ravi K and Tariq Ahmed at Beach Road Cafe regarding clearance fees."},

        # CASE-205: Hawala Syndicate Alpha (Cross-border financial routing)
        {"fir_no": "FIR-205-01", "case_id": "case-205", "police_station": "Crime Branch HQ", "date": "2026-07-10T11:00:00", "suspects": [{"name": "Ravi Kumar", "role": "account_holder"}, {"name": "Sanjay Singhal", "role": "hawala_operator"}], "complaint_text": "Hawala routing through domestic shell accounts including account A101 associated with Ravi Kumar."},
        {"fir_no": "FIR-205-02", "case_id": "case-205", "police_station": "Economic Offences Wing", "date": "2026-07-18T14:15:00", "suspects": [{"name": "Meera Joshi", "role": "director_apex"}, {"name": "Rohan Gupta", "role": "auditor"}], "complaint_text": "Apex Trading Pvt Ltd audited by Rohan Gupta declared bogus overseas consultancy expenses."},
        {"fir_no": "FIR-205-03", "case_id": "case-205", "police_station": "Crime Branch HQ", "date": "2026-07-25T16:50:00", "suspects": [{"name": "Sanjay Singhal", "role": "operator"}, {"name": "Zubair Merchant", "role": "courier"}], "complaint_text": "Cash courier Zubair Merchant intercepted carrying token serial matching Hawala ledger."},
        {"fir_no": "FIR-205-04", "case_id": "case-205", "police_station": "Economic Offences Wing", "date": "2026-08-02T10:30:00", "suspects": [{"name": "Kavita Reddy", "role": "fiduciary"}], "complaint_text": "Fiduciary accounts held at Global Trust Bank liquidated prior to regulatory audit."},

        # CASE-301: Illicit SIM Box & VoIP Bypass
        {"fir_no": "FIR-301-01", "case_id": "case-301", "police_station": "Cyber Cell Central", "date": "2026-05-12T13:20:00", "suspects": [{"name": "R. Kumar", "role": "subscriber", "phone": "9876543210"}, {"name": "Naveen Patel", "role": "telecom_engineer"}], "complaint_text": "Illegal 32-port GSM gateway detected in Velachery. Primary SIM batch registered under R. Kumar (Phone 9876543210)."},
        {"fir_no": "FIR-301-02", "case_id": "case-301", "police_station": "Velachery PS", "date": "2026-05-20T17:00:00", "suspects": [{"name": "Gaurav Sen", "role": "isp_agent"}], "complaint_text": "ISP connection leased to fictitious business without KYC validation by Gaurav Sen."},
        {"fir_no": "FIR-301-03", "case_id": "case-301", "police_station": "Cyber Cell Central", "date": "2026-05-29T11:45:00", "suspects": [{"name": "Naveen Patel", "role": "engineer"}, {"name": "Imran Qureshi", "role": "server_admin"}], "complaint_text": "SIP trunk routing logs confirm calls originating from overseas VoIP servers managed by Imran Qureshi."},
        {"fir_no": "FIR-301-04", "case_id": "case-301", "police_station": "Guindy PS", "date": "2026-06-05T15:10:00", "suspects": [{"name": "R. Kumar", "role": "leaseholder"}, {"name": "Sunil Varma", "role": "property_agent"}], "complaint_text": "Commercial unit rental agreement signed by R. Kumar for server rack placement."},

        # CASE-412: Vehicle Theft & Fake RTO Module
        {"fir_no": "FIR-412-01", "case_id": "case-412", "police_station": "Traffic Crime PS", "date": "2026-04-14T08:30:00", "suspects": [{"name": "Ravi Kumar", "role": "registered_owner", "vehicle": "TN01AB1234"}, {"name": "Dinesh Chawla", "role": "rto_agent"}], "complaint_text": "Registration document irregularity detected for sedan TN01AB1234 processed via Dinesh Chawla agency."},
        {"fir_no": "FIR-412-02", "case_id": "case-412", "police_station": "Tambaram PS", "date": "2026-04-22T19:00:00", "suspects": [{"name": "Harishankar", "role": "mechanic"}, {"name": "Babloo Yadav", "role": "chassis_stamper"}], "complaint_text": "Chassis number alteration workshop busted in Tambaram industrial estate."},
        {"fir_no": "FIR-412-03", "case_id": "case-412", "police_station": "Traffic Crime PS", "date": "2026-05-01T12:15:00", "suspects": [{"name": "Dinesh Chawla", "role": "agent"}, {"name": "Ajay Menon", "role": "forger"}], "complaint_text": "Seizure of 45 blank smart card registration certificates from Ajay Menon residence."},
        {"fir_no": "FIR-412-04", "case_id": "case-412", "police_station": "Tambaram PS", "date": "2026-05-18T16:40:00", "suspects": [{"name": "Somesh Paul", "role": "buyer"}], "complaint_text": "Interception of cloned vehicle on National Highway 45."}
    ]

    with open(os.path.join(DATA_DIR, "fir", "historical_firs.json"), "w") as f:
        json.dump(firs, f, indent=2)

    # 2. CDR Records (CSV)
    cdr_rows = [
        ["call_id", "case_id", "caller", "callee", "duration", "cell_tower", "timestamp"],
        ["CDR-001", "case-101", "9876543210", "9876543211", "340", "Central Station Tower", "2026-08-01T10:15:00"],
        ["CDR-002", "case-101", "9876543210", "9876543212", "120", "Central Station Tower", "2026-08-01T11:00:00"],
        ["CDR-003", "case-101", "9876543212", "9876543214", "450", "Anna Nagar Tower", "2026-08-03T14:40:00"],
        ["CDR-004", "case-101", "9876543214", "9876543210", "180", "T Nagar Tower", "2026-08-05T16:10:00"],
        ["CDR-005", "case-203", "9876543210", "9876543220", "290", "Harbour Gate 4 Tower", "2026-06-10T09:30:00"],
        ["CDR-006", "case-203", "9876543220", "9876543221", "510", "Royapuram Tower", "2026-06-15T19:00:00"],
        ["CDR-007", "case-301", "9876543210", "9876543230", "600", "Velachery Tower", "2026-05-12T13:45:00"],
        ["CDR-008", "case-301", "9876543230", "9876543231", "420", "Guindy Tower", "2026-05-20T17:15:00"],
        ["CDR-009", "case-205", "9876543210", "9876543240", "310", "Mount Road Tower", "2026-07-10T11:20:00"],
        ["CDR-010", "case-205", "9876543240", "9876543241", "480", "Nungambakkam Tower", "2026-07-18T14:30:00"],
        ["CDR-011", "case-412", "9876543210", "9876543250", "190", "Tambaram Tower", "2026-04-14T08:45:00"],
        ["CDR-012", "case-412", "9876543250", "9876543251", "240", "Tambaram Tower", "2026-04-22T19:20:00"],
    ]
    with open(os.path.join(DATA_DIR, "cdr", "historical_cdrs.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(cdr_rows)

    # 3. Financial Transactions (CSV)
    tx_rows = [
        ["tx_id", "case_id", "sender_account", "receiver_account", "amount", "currency", "bank", "timestamp"],
        ["TX-001", "case-101", "A101", "A102", "150000", "INR", "State Bank of India", "2026-08-01T12:00:00"],
        ["TX-002", "case-101", "A102", "A103", "145000", "INR", "HDFC Bank", "2026-08-02T15:30:00"],
        ["TX-003", "case-205", "A101", "A201", "500000", "INR", "State Bank of India", "2026-07-10T14:00:00"],
        ["TX-004", "case-205", "A201", "A202", "480000", "INR", "Axis Bank", "2026-07-12T16:45:00"],
        ["TX-005", "case-205", "A202", "A203", "450000", "INR", "ICICI Bank", "2026-07-15T11:10:00"],
        ["TX-006", "case-301", "A101", "A301", "75000", "INR", "State Bank of India", "2026-05-15T10:00:00"],
        ["TX-007", "case-203", "A201", "A101", "250000", "INR", "Axis Bank", "2026-06-18T13:20:00"],
        ["TX-008", "case-412", "A101", "A401", "120000", "INR", "State Bank of India", "2026-04-16T11:00:00"],
    ]
    with open(os.path.join(DATA_DIR, "financial", "historical_transactions.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(tx_rows)

    # 4. Surveillance Sightings (JSON)
    srv = [
        {"log_id": "SRV-01", "case_id": "case-101", "location": "Central Station", "subject_name": "Ravi Kumar", "vehicle_plate": "TN01AB1234", "notes": "Subject parked sedan and met Arun at platform 1 concourse.", "timestamp": "2026-08-01T09:45:00"},
        {"log_id": "SRV-02", "case_id": "case-203", "location": "Harbour Gate 4", "subject_name": "Ravi K", "vehicle_plate": "TN01AB1234", "notes": "Vehicle entered port terminal with clearance badge.", "timestamp": "2026-06-10T09:10:00"},
        {"log_id": "SRV-03", "case_id": "case-301", "location": "Velachery Tech Park", "subject_name": "R. Kumar", "vehicle_plate": "TN01AB1234", "notes": "Subject dropped hardware equipment box at service lift.", "timestamp": "2026-05-12T13:10:00"},
        {"log_id": "SRV-04", "case_id": "case-205", "location": "Mount Road Plaza", "subject_name": "Ravi Kumar", "vehicle_plate": "TN01AB1234", "notes": "Target entered Apex Trading regional office.", "timestamp": "2026-07-10T10:50:00"},
        {"log_id": "SRV-05", "case_id": "case-412", "location": "Tambaram RTO Office", "subject_name": "Ravi Kumar", "vehicle_plate": "TN01AB1234", "notes": "Target submitted duplicate RC application at counter 3.", "timestamp": "2026-04-14T08:15:00"},
    ]
    with open(os.path.join(DATA_DIR, "surveillance", "historical_surveillance.json"), "w") as f:
        json.dump(srv, f, indent=2)

    # 5. Criminal History Dossiers (JSON)
    dossiers = [
        {"dossier_id": "DOS-001", "case_id": "case-101", "name": "Ravi Kumar", "aliases": ["Ravi K", "R. Kumar", "RAVI KUMAR"], "known_phone": "9876543210", "known_vehicle": "TN01AB1234", "organizations": ["Apex Trading Pvt Ltd", "Shadow Net Syndicate"], "prior_charges": ["Section 420 IPC (Cheating)", "Section 66D IT Act", "Customs Act Section 132"]},
        {"dossier_id": "DOS-002", "case_id": "case-101", "name": "Arun", "aliases": ["Arun Driver", "Arun M"], "known_phone": "9876543211", "known_vehicle": "TN01AB1234", "organizations": ["Shadow Net Syndicate"], "prior_charges": ["Section 411 IPC (Stolen Property)"]},
        {"dossier_id": "DOS-003", "case_id": "case-205", "name": "Sanjay Singhal", "aliases": ["Singhal Bhai"], "known_phone": "9876543240", "known_vehicle": "MH01CD5678", "organizations": ["Apex Trading Pvt Ltd", "Hawala Syndicate Alpha"], "prior_charges": ["FEMA Contravention", "PMLA Section 3"]},
        {"dossier_id": "DOS-004", "case_id": "case-203", "name": "Manish Shah", "aliases": ["Shah Port"], "known_phone": "9876543220", "known_vehicle": "TN02EF9012", "organizations": ["Maritime Freight Lines"], "prior_charges": ["Customs Evasion"]},
        {"dossier_id": "DOS-005", "case_id": "case-301", "name": "Naveen Patel", "aliases": ["Telecom Naveen"], "known_phone": "9876543230", "known_vehicle": "KA03GH3456", "organizations": ["VoIP Gateway Solutions"], "prior_charges": ["Telegraph Act Section 20"]}
    ]
    with open(os.path.join(DATA_DIR, "criminal_history", "historical_dossiers.json"), "w") as f:
        json.dump(dossiers, f, indent=2)

    # 6. Intelligence Reports (JSON)
    intel = [
        {"report_id": "INTEL-001", "case_id": "case-101", "title": "Special Branch Bulletin - Cyber Hawala Linkage", "summary": "Intelligence indicates nexus between Chennai cyber fraudsters and Hawala conduit operating via Mount Road. Primary facilitator identified as Ravi Kumar coordinating logistics using phone 9876543210 and vehicle TN01AB1234.", "named_entities": [{"name": "Ravi Kumar", "type": "person"}, {"name": "9876543210", "type": "phone"}, {"name": "TN01AB1234", "type": "vehicle"}, {"name": "Central Station", "type": "location"}]},
        {"report_id": "INTEL-002", "case_id": "case-205", "title": "FIU Flash Alert - Shell Company Account Churn", "summary": "High volume cyclic wire transfers between Account A101 and secondary accounts in SBI and HDFC. Account belongs to key operative Ravi Kumar linked with Apex Trading Pvt Ltd.", "named_entities": [{"name": "Ravi Kumar", "type": "person"}, {"name": "A101", "type": "account"}, {"name": "Apex Trading Pvt Ltd", "type": "org"}]},
        {"report_id": "INTEL-003", "case_id": "case-301", "title": "Telecom Enforcement Lead - SIM Churn in Chennai Hub", "summary": "Multiple high-usage SIMs linked to subscriber identity R. Kumar activated across Velachery and Guindy. Traffic patterns indicate SIM box bypass operations.", "named_entities": [{"name": "R. Kumar", "type": "person"}, {"name": "9876543210", "type": "phone"}, {"name": "Velachery", "type": "location"}]}
    ]
    with open(os.path.join(DATA_DIR, "intelligence", "historical_intel.json"), "w") as f:
        json.dump(intel, f, indent=2)

    # 7. Vehicle Registrations (JSON)
    vehicles = [
        {"plate_number": "TN01AB1234", "owner_name": "Ravi Kumar", "model": "Maruti Suzuki Swift", "color": "Pearl White", "state": "Tamil Nadu"},
        {"plate_number": "MH01CD5678", "owner_name": "Sanjay Singhal", "model": "Toyota Fortuner", "color": "Black", "state": "Maharashtra"},
        {"plate_number": "TN02EF9012", "owner_name": "Manish Shah", "model": "Hyundai Creta", "color": "Silver", "state": "Tamil Nadu"},
        {"plate_number": "KA03GH3456", "owner_name": "Naveen Patel", "model": "Honda City", "color": "Grey", "state": "Karnataka"},
        {"plate_number": "DL04IJ7890", "owner_name": "Vikram Seth", "model": "Tata Nexon", "color": "Blue", "state": "Delhi"}
    ]
    with open(os.path.join(DATA_DIR, "vehicles", "historical_vehicles.json"), "w") as f:
        json.dump(vehicles, f, indent=2)

    # 8. Social Media Intelligence (JSON)
    social = [
        {"post_id": "SOC-001", "case_id": "case-101", "handle": "@shadow_ravi", "platform": "Telegram", "content": "Payment channels active on A101. Ping on 9876543210 for verification.", "linked_person": "Ravi Kumar"},
        {"post_id": "SOC-002", "case_id": "case-205", "handle": "@apex_singhal", "platform": "WhatsApp", "content": "Ledger token delivered to Central Station locker.", "linked_person": "Sanjay Singhal"},
        {"post_id": "SOC-003", "case_id": "case-301", "handle": "@voip_naveen", "platform": "Signal", "content": "32 port gateway running on 9876543210 pool.", "linked_person": "Naveen Patel"}
    ]
    with open(os.path.join(DATA_DIR, "social", "historical_social.json"), "w") as f:
        json.dump(social, f, indent=2)

    print(f"Controlled synthetic datasets generated successfully in: {DATA_DIR}")

if __name__ == "__main__":
    generate_datasets()
