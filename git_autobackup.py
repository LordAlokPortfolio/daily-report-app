    # … after your commit …
    repo = os.environ["REPO_URL"]
    if not repo.endswith(".git"):
        repo += ".git"
    token_url = repo.replace(
        "https://",
        f"https://{os.environ['GIT_TOKEN']}@"
    )

    # run push and capture output
    result = subprocess.run(
        ["git", "push", token_url, "HEAD:main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print("🛑 Push failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        raise subprocess.CalledProcessError(result.returncode, result.args)
    else:
        print("🔄 Backup pushed to GitHub.")
