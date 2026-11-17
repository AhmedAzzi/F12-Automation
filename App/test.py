from pywinauto import Application

window_titles = r"(VISION\s+RIS|GENERAL_LIGHT)"
app = Application(backend="uia").connect(title_re=window_titles)
dlg = app.window(title_re=window_titles)

items = dlg.descendants(control_type="DataItem")

patient_names = []

# Detect DataItem cells from column "Patient"
for item in items:
    txt = item.window_text()

    # Pattern: "Patient Ligne X"
    if txt.startswith("Patient Ligne"):
        try:
            # The REAL text is inside the Value pattern (UIA Value)
            value = item.iface_value.CurrentValue
        except:
            value = ""

        # Store only non-empty real names
        if value.strip():
            patient_names.append(value.strip())

# Save to file
with open("patients.txt", "w", encoding="utf-8") as f:
    for name in patient_names:
        f.write(name + "\n")

print("\n=== PATIENT NAMES FOUND ===")
for i, name in enumerate(patient_names, 1):
    print(f"{i}: {name}")

print("\n📁 Saved to patients.txt")
