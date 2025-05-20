from App import create_app, db
from App.models.Visamodels import VisaProject
import sys

def update_visa_projects(dry_run=False, limit=None):
    """
    Update visa projects by extracting information from project_folder_name.
    
    Args:
        dry_run (bool): If True, don't save changes to database (test mode)
        limit (int): Optional limit on number of records to process
    """
    # Create app context
    app = create_app()
    with app.app_context():
        # Get all visa projects
        projects = VisaProject.query.all()
        
        # Apply limit if specified
        if limit and limit > 0:
            projects = projects[:limit]
            print(f"Limited to processing {limit} projects for testing")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"Found {len(projects)} visa projects to process.")
        print(f"Running in {'TEST MODE' if dry_run else 'LIVE MODE'}")
        
        # Valid singapore status values for identification
        valid_statuses = ['PR', '工作准证', '家属准证', '学生准证', '女佣准证']
        
        for project in projects:
            try:
                # Skip if project_folder_name is empty
                if not project.project_folder_name:
                    skipped_count += 1
                    print(f"Skipping project ID {project.id}: project_folder_name is empty")
                    continue
                
                print(f"\nProcessing project ID {project.id}: '{project.project_folder_name}'")
                
                # Split the project_folder_name by underscore
                parts = project.project_folder_name.split('_')
                
                # Check if we have enough parts to extract information
                if len(parts) < 3:
                    print(f"Skipping project ID {project.id}: '{project.project_folder_name}' doesn't have enough parts")
                    skipped_count += 1
                    continue
                
                # Extract information with better handling of name parts
                # For project names like: 韩国签证_HID168970_HE MIAO_工作准证
                # Or more complex names like: 韩国签证_HID168970_HE_MIAO_工作准证
                
                visa_type = parts[0]
                hid_or_serial = parts[1]
                
                # Check if the last part is a valid singapore_status
                singapore_status = None
                if parts[-1] in valid_statuses:
                    singapore_status = parts[-1]
                    # Name is everything between hid_or_serial and singapore_status
                    applicant_name = '_'.join(parts[2:-1])
                else:
                    # Name is everything after hid_or_serial
                    applicant_name = '_'.join(parts[2:])
                
                print(f"  Current values:")
                print(f"    - visa_type: {project.visa_type or 'None'}")
                print(f"    - hid_or_serial: {project.hid_or_serial or 'None'}")
                print(f"    - applicant_name: {project.applicant_name or 'None'}")
                print(f"    - singapore_status: {project.singapore_status or 'None'}")
                
                changed = False
                changes = []
                
                # Update visa_type if empty
                if not project.visa_type and visa_type:
                    if not dry_run:
                        project.visa_type = visa_type
                    changes.append(f"visa_type: {visa_type}")
                    changed = True
                    
                # Update hid_or_serial if empty
                if not project.hid_or_serial and hid_or_serial:
                    if not dry_run:
                        project.hid_or_serial = hid_or_serial
                    changes.append(f"hid_or_serial: {hid_or_serial}")
                    changed = True
                    
                # Update applicant_name if empty
                if not project.applicant_name and applicant_name:
                    if not dry_run:
                        project.applicant_name = applicant_name
                    changes.append(f"applicant_name: {applicant_name}")
                    changed = True
                    
                # Update singapore_status if empty and available
                if not project.singapore_status and singapore_status:
                    if not dry_run:
                        project.singapore_status = singapore_status
                    changes.append(f"singapore_status: {singapore_status}")
                    changed = True
                
                if changed:
                    updated_count += 1
                    print(f"  {'Would update' if dry_run else 'Updated'} with:")
                    for change in changes:
                        print(f"    - {change}")
                else:
                    skipped_count += 1
                    print(f"  No changes needed")
                    
            except Exception as e:
                error_count += 1
                print(f"Error processing project ID {project.id}: {str(e)}")
        
        # Commit changes to database
        if not dry_run:
            try:
                db.session.commit()
                print(f"\nChanges saved to database.")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing changes to database: {str(e)}")
        else:
            print(f"\nDry run - no changes saved to database.")
        
        print(f"\nSummary:\n- {updated_count} projects {'would be' if dry_run else 'were'} updated\n- {skipped_count} projects skipped\n- {error_count} errors")

if __name__ == "__main__":
    # Check if running in test mode
    dry_run = "--dry-run" in sys.argv or "-t" in sys.argv
    
    # Check for limit parameter
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i+1 < len(sys.argv):
            try:
                limit = int(sys.argv[i+1])
            except ValueError:
                print("Error: --limit must be followed by a number")
                sys.exit(1)
    
    # If user asked to test 2 records without specifying --limit
    if not limit and ("--test-2" in sys.argv or "--test2" in sys.argv):
        limit = 2
    
    # Print usage info
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python update_visa_data.py [options]")
        print("Options:")
        print("  --dry-run, -t     Run in test mode without saving changes")
        print("  --limit N         Process only N records")
        print("  --test-2          Process only 2 records (shortcut for --limit 2)")
        print("  --help, -h        Show this help message")
        sys.exit(0)
    
    update_visa_projects(dry_run=dry_run, limit=limit) 