from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from filemanager.models import Category, KnowledgeBaseArticle
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed categories, groups, and knowledge base articles for demo/testing.'

    def handle(self, *args, **options):
        # Create groups
        groups_data = [
            'IT Support Team',
            'Security Team',
            'Account Support Team',
            'Network Administrator',
            'Admin',
        ]
        
        for group_name in groups_data:
            group, created = Group.objects.get_or_create(name=group_name)
            verb = 'Created' if created else 'Exists'
            self.stdout.write(self.style.SUCCESS(f"{verb} group: {group.name}"))
        
        # Create categories
        categories_data = [
            {'name': 'Password Compromise', 'slug': 'password-compromise', 'is_security': False, 'default_assignee_group': 'Account Support Team'},
            {'name': 'Malware', 'slug': 'malware', 'is_security': True, 'default_assignee_group': 'Security Team'},
            {'name': 'Phishing', 'slug': 'phishing', 'is_security': True, 'default_assignee_group': 'Security Team'},
            {'name': 'Unauthorized Access', 'slug': 'unauthorized-access', 'is_security': True, 'default_assignee_group': 'Admin'},
            {'name': 'Network Attack', 'slug': 'network-attack', 'is_security': True, 'default_assignee_group': 'Network Administrator'},
            {'name': 'Data Breach', 'slug': 'data-breach', 'is_security': True, 'default_assignee_group': 'Security Team'},
            {'name': 'Account Lockout', 'slug': 'account-lockout', 'is_security': False, 'default_assignee_group': 'Account Support Team'},
            {'name': 'VPN Connectivity', 'slug': 'vpn-connectivity', 'is_security': False, 'default_assignee_group': 'Network Administrator'},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(slug=cat_data['slug'], defaults=cat_data)
            verb = 'Created' if created else 'Exists'
            self.stdout.write(self.style.SUCCESS(f"{verb} category: {category.name}"))
        
        # Create knowledge base articles
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING("No superuser found; skipping KB articles"))
            return
        
        kb_articles_data = [
            {
                'title': 'Password Compromise Recovery',
                'slug': 'password-compromise-recovery',
                'content': """Step 1: Isolate the affected account
- Disable the account immediately or force a password reset
- Review login history for unauthorized access

Step 2: Reset the password
- Use a secure, temporary password (20+ characters)
- Force the user to change it on next login
- Enable MFA if available

Step 3: Review account activity
- Check email forwarding rules
- Review recent file access and deletions
- Verify recovery email/phone on file

Step 4: Notify the user
- Inform them of the compromise
- Advise on signs of identity theft
- Provide guidance on credential hygiene

Step 5: Close the ticket
- Document the actions taken
- Note the timeline of the breach
- Schedule a follow-up in 7 days
"""
            },
            {
                'title': 'Phishing Email Response',
                'slug': 'phishing-email-response',
                'content': """Step 1: Do not click links or open attachments
- Advise the user to NOT reply to the email
- Do not download any files from the suspicious email

Step 2: Report the email
- Forward to security@company.com with full headers
- Submit to phishing report portal

Step 3: Check for compromise indicators
- Run endpoint protection scan
- Review browser history for suspicious sites
- Check for unauthorized account access

Step 4: Reset credentials
- Reset password immediately
- Enable or re-verify MFA
- Check saved passwords in browser

Step 5: Share intelligence
- Add the sender domain to blocklist
- Alert other users to watch for similar emails
- Document the phishing campaign details

Step 6: Close ticket
- Mark as resolved once user confirms
- Link to security awareness training
"""
            },
            {
                'title': 'Malware Incident Response',
                'slug': 'malware-incident-response',
                'content': """Step 1: Isolate the infected system
- Disconnect from network (both Ethernet and WiFi)
- Do NOT power down the machine (preserve forensic evidence)

Step 2: Preserve evidence
- Image the hard drive if possible
- Capture memory dump for analysis
- Document the symptoms and timeline

Step 3: Scan and clean
- Boot into safe mode with networking
- Download latest malware definitions
- Run full system scan with antivirus/anti-malware
- Consider professional incident response if critical

Step 4: Verify clean
- Run multiple scans from different vendors
- Check for persistence mechanisms (scheduled tasks, registry)
- Verify file integrity on critical system files

Step 5: Restore access
- Reconnect to network after clearance
- Monitor for re-infection
- Educate user on how malware was delivered

Step 6: Post-incident
- Update incident ticket with findings
- Share IOCs (indicators of compromise) with security team
- Review email security logs for similar campaigns
"""
            },
            {
                'title': 'Account Lockout Troubleshooting',
                'slug': 'account-lockout-troubleshooting',
                'content': """Step 1: Verify the lockout
- Check Active Directory user properties
- Look for account disabled flag
- Note the lockout time

Step 2: Determine the cause
- Review security event logs for failed login attempts
- Check for automated credential attempts
- Verify if user entered wrong password multiple times

Step 3: Unlock the account
- Open Active Directory Users and Computers
- Find the user account
- Uncheck 'Account is locked out' checkbox
- Apply changes

Step 4: Reset password (if needed)
- Right-click user → Reset Password
- Set temporary password
- Force user to change at next logon

Step 5: Address root cause
- If password guessing: advise on strong passwords and MFA
- If automated attack: check for credential cache on other systems
- If misconfiguration: verify desktop/application settings

Step 6: Document and close
- Note the resolution in ticket
- Advise user to change password on other systems
"""
            },
            {
                'title': 'Unauthorized Access Detection',
                'slug': 'unauthorized-access-detection',
                'content': """Step 1: Confirm the breach
- Review access logs for the user account
- Check IP addresses and login times
- Verify geography (impossible travel?)

Step 2: Identify scope
- Check what data was accessed
- Review file modifications and deletions
- Check email forwarding rules and shared folder access

Step 3: Immediate response
- Change user password
- Revoke all active sessions
- Reset API keys and tokens
- Revoke application access

Step 4: Notify stakeholders
- Inform user of the breach
- Alert management
- Notify security team
- Prepare breach notification if sensitive data exposed

Step 5: Forensic analysis
- Preserve logs and evidence
- Engage incident response team
- Document findings for legal/compliance

Step 6: Remediation
- Implement multi-factor authentication
- Review access controls and permissions
- Conduct security awareness training for user
"""
            },
        ]
        
        for kb_data in kb_articles_data:
            kb, created = KnowledgeBaseArticle.objects.get_or_create(
                slug=kb_data['slug'],
                defaults={
                    'title': kb_data['title'],
                    'content': kb_data['content'],
                    'created_by': admin_user,
                }
            )
            verb = 'Created' if created else 'Exists'
            self.stdout.write(self.style.SUCCESS(f"{verb} KB article: {kb.title}"))
        
        self.stdout.write(self.style.SUCCESS('\n✓ All seed data loaded successfully!'))
