import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Push games.db changes to GitHub main branch using PAT authentication"

    def handle(self, *args, **options):
        # Get the GitHub PAT from environment
        github_pat = os.environ.get("GITHUB_PAT")
        if not github_pat:
            self.stderr.write(
                self.style.ERROR(
                    "GITHUB_PAT environment variable not set. Cannot push to GitHub."
                )
            )
            return

        try:
            # Check if there are any changes to games.db
            result = subprocess.run(
                ["git", "status", "--porcelain", "games.db"],
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                # No changes to games.db, exit silently
                return

            # Configure git user for this commit
            subprocess.run(
                ["git", "config", "user.name", "Automated"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "actions@users.noreply.github.com"],
                check=True,
                capture_output=True,
            )

            # Add games.db to staging
            subprocess.run(
                ["git", "add", "games.db"],
                check=True,
                capture_output=True,
            )

            # Get the current timestamp
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Commit with ❄️ emoji
            commit_message = f"❄️ Updated games.db: {timestamp}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
            )

            # Get the repository URL and replace with authenticated URL
            result = subprocess.run(
                ["git", "config", "get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
            )
            repo_url = result.stdout.strip()

            # Convert HTTPS URL to use PAT authentication
            # Assumes format: https://github.com/owner/repo.git
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace(
                    "https://github.com/",
                    f"https://x-access-token:{github_pat}@github.com/",
                )

            # Push to main using PAT
            subprocess.run(
                ["git", "push", repo_url, "main"],
                check=True,
                capture_output=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully pushed games.db to main: {timestamp}"
                )
            )

        except subprocess.CalledProcessError as e:
            self.stderr.write(
                self.style.ERROR(
                    f"Git operation failed: {e.stderr if e.stderr else str(e)}"
                )
            )
