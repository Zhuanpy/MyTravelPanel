-- Add new columns to visa_projects table
ALTER TABLE visa_projects ADD COLUMN visa_type VARCHAR(50);
ALTER TABLE visa_projects ADD COLUMN applicant_name VARCHAR(100);
ALTER TABLE visa_projects ADD COLUMN contact_name VARCHAR(100);
ALTER TABLE visa_projects ADD COLUMN remarks TEXT; 