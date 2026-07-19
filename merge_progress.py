import os
import csv
import shutil

def normalize(val):
    return str(val).strip().lower()

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    f_asset = os.path.join(workspace_dir, "AssetF.csv")
    f_rec = os.path.join(workspace_dir, "AssetF_recovered.csv")
    f_scraped = os.path.join(workspace_dir, "scraped_leads.csv")
    f_backup = os.path.join(workspace_dir, "AssetF_recovered_backup.csv")

    if not os.path.exists(f_rec):
        print(f"Error: Target file '{f_rec}' does not exist.")
        return

    # Step 1: Create backup
    print(f"Backing up '{f_rec}' to '{f_backup}'...")
    shutil.copy2(f_rec, f_backup)

    # Step 2: Load completed emails from previous runs
    email_map = {}

    def load_to_map(file_path, label):
        if not os.path.exists(file_path):
            print(f"Warning: {label} file '{file_path}' not found. Skipping.")
            return
        
        count = 0
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = normalize(row.get("Business Name", ""))
                phone = normalize(row.get("Phone Number", ""))
                if phone.endswith(".0"):
                    phone = phone[:-2]
                email = row.get("Email", "").strip()
                
                if name and email and email != "NOT_FOUND" and email != "":
                    key = (name, phone)
                    email_map[key] = email
                    count += 1
        print(f"Loaded {count} valid emails from {label}.")

    load_to_map(f_scraped, "scraped_leads.csv")
    load_to_map(f_asset, "AssetF.csv")
    print(f"Total unique email mapping entries collected: {len(email_map)}")

    # Step 3: Update AssetF_recovered.csv
    updated_rows = []
    restored_count = 0
    total_count = 0
    fieldnames = []

    with open(f_rec, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            total_count += 1
            name = normalize(row.get("Business Name", ""))
            phone = normalize(row.get("Phone Number", ""))
            if phone.endswith(".0"):
                phone = phone[:-2]
            email = row.get("Email", "").strip()

            if not email or email == "NOT_FOUND" or email == "":
                key = (name, phone)
                if key in email_map:
                    row["Email"] = email_map[key]
                    restored_count += 1
            updated_rows.append(row)

    # Step 4: Write back updated rows
    with open(f_rec, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\nMerge Complete!")
    print(f"Total rows in 'AssetF_recovered.csv': {total_count}")
    print(f"Successfully restored/merged: {restored_count} emails.")
    print(f"Remaining empty emails left to enrich: {total_count - (restored_count + 2)}") # 2 were already filled

if __name__ == "__main__":
    main()
