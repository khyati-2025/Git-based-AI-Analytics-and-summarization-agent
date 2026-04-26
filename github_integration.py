
class GitAgent:
    def __init__(self, token=None, base_url=None):
        self.token = token or os.getenv("token")
        if not self.token:
            raise ValueError("GitHub Token is required. Set GITHUB_TOKEN environment variable or pass it to the constructor.")

        if base_url:
            self.g = Github(auth=github.Auth.Token(self.token), base_url=base_url)
        else:
            self.g = Github(auth=github.Auth.Token(self.token))

        self.repo = None

    @staticmethod
    def parse_repo_url(repo_url: str):
        ssh_pattern = r"git@([^:]+):(.+?)/(.+?)(\.git)?$"
        ssh_match = re.match(ssh_pattern, repo_url.strip())

        if ssh_match:
            return {
                "host": ssh_match.group(1),
                "owner": ssh_match.group(2),
                "repo": ssh_match.group(3).replace(".git", "")
            }

        parsed = urlparse(repo_url.strip())
        if parsed.scheme in ("http", "https"):
            parts = parsed.path.strip("/").replace(".git", "").split("/")
            if len(parts) >= 2:
                return {
                    "host": parsed.hostname,
                    "owner": parts[-2],
                    "repo": parts[-1]
                }

        raise ValueError(f"Invalid Git repository URL: {repo_url}")

    def connect(self, repo_url: str):
        try:
            details = self.parse_repo_url(repo_url)
            repo_full_name = f"{details['owner']}/{details['repo']}"
            self.repo = self.g.get_repo(repo_full_name)

            perms = self.repo.permissions
            if perms.pull == False:
                raise ConnectionError("Insufficient permissions to access the repository. Read (Pull) access is required.")


            try:
                limit = self.g.get_rate_limit()
                if hasattr(limit, 'core'):
                    remaining = limit.core.remaining
                elif hasattr(limit, 'rate'):
                    remaining = limit.rate.remaining
                else:
                    remaining = None

                if remaining is not None and remaining < 10:
                   print(f"Warning: low rate limit ({remaining} requests left).")
            except Exception:
                pass

            return {
                "full_name": self.repo.full_name,
                "permissions": {
                    "read": perms.pull,
                    "write": perms.push,
                    "admin": perms.admin
                }
            }
        except GithubException as e:
            if e.status == 401:
                raise ConnectionError("Authentication Failed: 401 Unauthorized. Please check if your GITHUB_TOKEN is valid and not expired.")
            elif e.status == 403:
                raise ConnectionError("Access Denied: 403 Forbidden. Your token might lack the 'repo' scope or access to this private repository.")
            elif e.status == 404:
                raise ConnectionError("Repository Not Found: 404. Please check the URL and ensure your token has access to this repo.")
            else:
                raise ConnectionError(f"GitHub API Error: {e.status} - {e.data.get('message', str(e))}")
        except Exception as e:
            raise ConnectionError(f"An error occurred while connecting: {str(e)}")

    def get_commits(self, since=datetime(datetime.now().year, datetime.now().month, datetime.now().day), until=None, author=None, branch=None):
        if not self.repo:
            raise RuntimeError("Agent is not connected to any repository. Call connect() first.")

        params = {}
        if since: params['since'] = since
        if until: params['until'] = until
        if author: params['author'] = author
        if branch: params['sha'] = branch

        try:
            commits = self.repo.get_commits(**params)

            if commits.totalCount == 0:
                print("No commits found for the specified parameters.")
                return []
            return commits

        except GithubException as e:

            if e.status == 403 and "secondary rate limit" in str(e).lower():
                print("Error: Hit GitHub Secondary Rate Limit. Try reducing the date range.")
            elif e.status == 409:
                print("Error: Git Repository is empty or branch not found.")
            else:
                print(f"Error retrieving commits: {e.data.get('message', e)}")
            return []

        except Exception as e:
            print(f"Error retrieving commits: {e}")
            return []

    def parse_commit_data(self, commit):
        try:
            commit_info = commit.commit
            author_info = commit_info.author

            try:
                stats = commit.stats
                additions = stats.additions
                deletions = stats.deletions
            except Exception:
                additions = 0
                deletions = 0

            file_details = []
            try:
                files = commit.files
                if hasattr(files, "totalCount"):
                    files_changed = files.totalCount
                else:
                    files_changed = len(files)

                for f in files:
                    file_details.append({
                        "filename": f.filename,
                        "status": f.status,
                        "additions": f.additions,
                        "deletions": f.deletions,
                        "patch": f.patch
                    })
            except Exception:
                files_changed = 0

            return {
                "hash": commit.sha,
                "author": author_info.name or "Unknown",
                "email": author_info.email or "Unknown",
                "message": commit_info.message,
                "timestamp": author_info.date,
                "files_changed": files_changed,
                "file_details": file_details,
                "additions": additions,
                "deletions": deletions
            }
        except Exception as e:
            print(f"Error parsing commit {commit.sha}: {e}")
            return None

    def get_statistics(self, commits):
        total_commits = 0
        total_files_changed = 0
        total_additions = 0
        total_deletions = 0
        contributors = set()
        contributor_stats = defaultdict(lambda: {"commits": 0, "additions": 0, "deletions": 0})

        for commit in commits:
            data = self.parse_commit_data(commit)
            if not data:
                continue

            total_commits += 1
            total_files_changed += data["files_changed"]
            total_additions += data["additions"]
            total_deletions += data["deletions"]
            contributors.add(data["author"])

            c_stats = contributor_stats[data["author"]]
            c_stats["commits"] += 1
            c_stats["additions"] += data["additions"]
            c_stats["deletions"] += data["deletions"]

        return {
            "total_commits": total_commits,
            "total_contributors": len(contributors),
            "total_files_changed": total_files_changed,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "per_contributor": dict(contributor_stats),
        }

    def load_repo_list(self, file_path: str) -> list[str]:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]

    def fetch_repo_stats(self, repo_url: str, since: datetime, until: datetime, author: str):
            try:
                self.connect(repo_url)
                commits = self.get_commits(since=since, until=until, author=author)
                ''' if since is None:
                    throw Exception("[ERROR]: -------> Since date is required")
                if until is None:
                    throw Exception("[ERROR]: -------> Until date is required")
                if since > until:
                    throw Exception("[ERROR]: -------> Since date should be less than Until date")
                if since == until:
                    throw Exception("[ERROR]: -------> Since date and Until date cannot be same. Minium duration of 30days")
                if since - until > timedelta(days=30):
                    throw Exception("[ERROR]: -------> Since date and Until date cannot be more than 30days") '''


                parsed = []
                for commit in commits:
                    data = self.parse_commit_data(commit)
                    if data:
                        data['repo_url'] = repo_url  # Add repo context
                        parsed.append(data)


                return parsed

            except Exception as e:
                print(f"Error fetching repository stats: {e}")
                return None

    def aggregate_to_dataframe(self, stats_list):
            df = pd.DataFrame([item for sublist in stats_list for item in sublist])
            df.to_csv("repo_stats.csv", index=False)
            return df

    def compute_churn(self, df: pd.DataFrame, top_n: int = 10):
            """Flatten nested file details and compute churn grouped by repo/file."""
            flattened_files = []
            for _, row in df.iterrows():
                repo_url = row.get('repo_url', 'Unknown')
                for f in row.get('file_details', []):
                    flattened_files.append({
                        'repo_url': repo_url,
                        'filename': f['filename'],
                        'additions': f['additions'],
                        'deletions': f['deletions']
                    })

            if not flattened_files:
                return pd.DataFrame(columns=['repo_url', 'filename', 'additions', 'deletions', 'churn_ratio'])

            file_df = pd.DataFrame(flattened_files)
            churn = file_df.groupby(['repo_url', 'filename']).agg({
                'additions': 'sum',
                'deletions': 'sum'
            }).reset_index()
            churn["churn_ratio"] = churn["additions"] / (churn["additions"] + churn["deletions"]).replace(0,1)
            churn = churn.sort_values("churn_ratio", ascending=False).head(top_n)

            # Save churn analysis to CSV as requested
            churn.to_csv("churn_analysis.csv", index=False)
            print(f"[SUCCESS] Churn analysis stored in churn_analysis.csv")

            return churn

    def classify_commits(self, message: str):
            msg = message.lower()
            if re.search(r"fix|bug|issues|patch", msg):
                return "bugfix"

            if re.search(r"feature|add|implement", msg):
                return "feature"

            if re.search(r"docs|document|documentation|readme|markdown", msg):
                return "documentation"

            if re.search(r"refactor|refactoring|cleanup|restructure", msg):
                return "refactor"

            if re.search(r"test|testing|unittest|pytest", msg):
                return "testing"

            return "other"

    def enrich_with_classifications(self, df: pd.DataFrame):
            df['category'] = df['message'].apply(self.classify_commits)
            return df

    def summarise_patches(self, df: pd.DataFrame, top_churn: pd.DataFrame, author:str, start: datetime, end: datetime) -> pd.DataFrame:
            """Find patches for the high-churn files and generate LLM summaries."""
            # Pre-flatten for easier patch lookup
            flattened_patches = []
            for _, row in df.iterrows():
                repo_url = row.get('repo_url', 'Unknown')
                for f in row.get('file_details', []):
                    if f.get('patch'):
                        flattened_patches.append({
                            'repo_url': repo_url,
                            'filename': f['filename'],
                            'patch': f['patch']
                        })

            patch_df = pd.DataFrame(flattened_patches)

            summaries = []
            for _, row in top_churn.iterrows():
                repo_url = row['repo_url']
                filename = row['filename']

                # Find the most recent patch for this file in this repo
                if not patch_df.empty:
                    relevant = patch_df[(patch_df['repo_url'] == repo_url) & (patch_df['filename'] == filename)]
                    patch = relevant['patch'].iloc[0] if not relevant.empty else None
                else:
                    patch = None

                if patch:
                    summary = smart_summary_fallback(patch[:2000],
                         author,
                         start.date(),
                         end.date())
                else:
                    summary = "No patch is available"
                summaries.append(summary)

            top_churn = top_churn.copy()
            top_churn['Change_summary'] = summaries

            return top_churn


    def forecast_trends(self, df: pd.DataFrame):
            """Linear forecast of commits per day for the next week."""
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            daily = df.groupby(df["timestamp"].dt.date).size()
            x = np.arange(len(daily))
            y = daily.values
            if len(x) < 2:
                return {"next_week": int(y.sum()), "slope": 0.0}
            slope, intercept = np.polyfit(x, y, 1)
            future_x = np.arange(len(daily), len(daily) + 7)
            forecast_vals = np.polyval([slope, intercept], future_x)
            next_week = int(max(forecast_vals.sum(), 0))
            return {"next_week": next_week, "slope": float(slope)}

    def generate_report(
            self,
            df: pd.DataFrame,
            churn_df: pd.DataFrame,
            forecast: dict,
            author: str,
            start: datetime,
            end: datetime,
        ) -> str:
            """Compose the final markdown report."""
            # High‑level narrative (uses existing LLM fallback)
            overview_text = "\n".join(df["message"].tolist())
            narrative = smart_summary_fallback(
                overview_text, author, start.date(), end.date()
            )
            # Churn table in markdown
            churn_md = churn_df.to_markdown(index=False)
            # Forecast section
            forecast_md = f"**Next‑week commit forecast:** {forecast['next_week']} commits (trend slope = {forecast['slope']:.2f})"
            report = f"""# Git Repository Analytics Report
                **Period:** {start.date()} → {end.date()}
                **Author:** {author or 'All contributors'}
                ---
                ## Overview Narrative
                {narrative}
                ---
                ## Top Churn Files (ratio)
                {churn_md}
                ---
                ## Trend Forecast
                {forecast_md}
                ---
                *Report generated automatically by the GitAgent pipeline.*"""
            return report


def llm_speed_hf(model_id, activity_text, author, date=None, end=None):
  if date is None:
    date = datetime.now().date()
  if end is None:
    end = date

  system_prompt =  f"""
    You are an assistant with a tech background.
    Your job is to create a report on the changes made in a Git repository.
    Summarize the content of the changes over the specified duration.
    Format the output as a structured report.
    Include a section titled 'Chronological Activity Timeline' that lists the key changes mapped to their specific dates
    Moreover, you should mention the name of the contributor {author} and the date of which the report from {date} to {end} generated.
    Provide without any emoji or any other special symbols like hashtags.
    Arrange and do organise the content in a proper manner professional report manner.

    """

  try:
    # Using HuggingFaceEndpoint directly for better compatibility with LangChain
    hf_llm_endpoint = HuggingFaceEndpoint(
        repo_id=model_id,
        huggingfacehub_api_token=os.getenv('HF_TOKEN'),
        temperature=0.7,
        max_new_tokens=1500,
        # It's important to pass stop_sequences to the endpoint directly for chat models
        stop_sequences=["<|user|>", "<|assistant|>", "<|endoftext|>", "</s>", "<|im_end|>"]
    )

    chat_model = ChatHuggingFace(llm=hf_llm_endpoint)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=activity_text),
    ]

    start_time = time.time()
    response = chat_model.invoke(messages)
    speed = time.time() - start_time
    print(f"    --------->[Speed-test] {model_id} used speed: {speed:.2f} seconds")
    return speed

  except Exception as e:
    print(f"HuggingFace Inference Error for {model_id}: {e}")
    return None


def llm_summarise(activity_text, author, date=None, end=None, total_file=None, total_add=None, total_del=None):
    if date is None:
        date = datetime.now().date()

    if end is None:
        end = date

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5)

    system_prompt =  f"""
    You are an assistant with a tech background.
    Your job is to create a report on the changes made in a Git repository.
    Summarize the content of the changes over the specified duration.
    Format the output as a structured report.
    Include a section titled 'Chronological Activity Timeline' that lists the key changes mapped to their specific dates
    Moreover, you should mention the name of the contributor {author} and the date of which the report from {date} to {end} generated.
    Provide without any emoji or any other special symbols like hashtags.
    Arrange and do organise the content in a proper manner professional report manner.
    At the start of the report include the total number of files {  total_file} changed, total number of additions {total_add} and total number of deletions {total_del}.
    """


    try:
        start = time.time()
        messages = [
            ("system", system_prompt),
            ("user", activity_text),
        ]


        response = llm.invoke(messages)
        speed = time.time() - start
        print(f"-----------------------------------------speed {speed}")
        return response.content

    except Exception as e:
        print(f"\n--- AI Summarization Failed ---")
        print(f"Error: {e}")
        print("Note: Ensure your GOOGLE_API_KEY is correct and you have quota available.")

def llm_summarise_hf(activity_text, author, date=None, end=None, total_file=None, total_add=None, total_del=None):
    if date is None:
        date = datetime.now().date()
    if end is None:
      end = date

    instruction = f"""
    You are an assistant with a tech background.
    Your job is to create a report on the changes made in a Git repository.
    Summarize the content of the changes over the specified duration.
    Format the output as a structured report.
    Include a section titled 'Chronological Activity Timeline' that lists the key changes mapped to their specific dates
    Moreover, you should mention the name of the contributor {author} and the date of which the report from {date} to {end} generated.
    Provide without any emoji or any other special symbol like hashtags.
    Arrange and do organise the content in a proper manner professional report manner.
    At the start of the report include the total number of files {total_file} changed, total number of additions {total_add} and total number of deletions {total_del}.
    """

    try:
      client = InferenceClient(
          model="google/gemma-2-9b-it",
          token=os.getenv('HF_TOKEN')
      )


      final_content = (
          f"Data to summarize:\n"
          f"{activity_text}\n\n"
          f"Task: Write a concise natural language summary of the above changes. Mention contributor {author}. Do not output any code."
      )

      start = time.time()

      response = client.chat_completion(
          messages=[
              {
                  "role": "system",
                  "content": instruction
              },
              {
                  "role": "user",
                  "content": final_content
              },

                   ],
           max_tokens = 1500,
           temperature = 0.1,
           stop = ["<|user|>", "<|assistant|>", "</s>"]
      )
      speed = time.time() - start
      print(f"----------------------------------------->>>>Speed {speed}")
      return response.choices[0].message.content.strip()


    except Exception as e:
        print(f"HuggingFace Inference Error: {e}")
        return None



def llm_summarise_hf2(activity_text, author, date=None, end=None, total_file=None, total_add=None, total_del=None):
    if date is None:
        date = datetime.now().date()
    if end is None:
      end = date

    instruction = f"""
    You are an assistant with a tech background.
    Your job is to create a report on the changes made in a Git repository.
    Summarize the content of the changes over the specified duration.
    Format the output as a structured report.
    Include a section titled 'Chronological Activity Timeline' that lists the key changes mapped to their specific dates
    Moreover, you should mention the name of the contributor {author} and the date of which the report from {date} to {end} generated.
    Provide without any emoji or any other special symbol like hashtags.
    Arrange and do organise the content in a proper manner professional report manner.
    At the start of the report include the total number of files {total_file} changed, total number of additions {total_add} and total number of deletions {total_del}.
    """

    try:
      client = InferenceClient(
          model="google-t5/t5-base",
          token=os.getenv('HF_TOKEN')
      )


      final_content = (
          f"Data to summarize:\n"
          f"{activity_text}\n\n"
          f"Task: Write a concise natural language summary of the above changes. Mention contributor {author}. Do not output any code."
      )

      start = time.time()

      response = client.text_generation(
         instruction + "\n\n" + final_content,
         max_new_tokens=1500,
         temperature=0.1,
         stop=["<|user|>", "<|assistant|>", "</s>"]

      )
      speed = time.time() - start
      print(f"----------------------------------------->>>>Speed {speed}")
      return response.strip()


    except Exception as e:
        print(f"HuggingFace Inference Error: {e}")
        return None




def map_reduce_summarise(activity_text_list, author, date=None, end=None, chunk=12000, total_file=None, total_add=None, total_del=None):

    try:
        if date is None:
            date = datetime.now().date()
        if end is None:
            end = date


        full_text = "\n".join(activity_text_list)
        char_count = len(full_text)

        print(f"\n[Map-Reduce] Starting recursive summarization for {char_count} chars...")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk,
            chunk_overlap=500,
            separators=["\nCOMMIT:", "\n", " "]
        )

        chunks = text_splitter.create_documents([full_text])
        mini_summaries = []

        print(f"[Map-Reduce] Split into {len(chunks)} text chunks (approx {chunk} chars each).")

        for i, chunk in enumerate(chunks):
            print(f"  - Summarizing chunk {i+1}/{len(chunks)} (size: {len(chunk.page_content)})...")
            batch_text = chunk.page_content


            mini_summary = smart_summary_fallback(batch_text, author, f"{date} (Partial Chunk {i+1})", f"{end}", total_file, total_add, total_del)
            if mini_summary:
                mini_summaries.append(mini_summary)


        print(f"\n[Map-Reduce] Aggregating {len(mini_summaries)} mini-summaries...")
        final_input = "Here is a collection of partial summaries from the repository history:\n\n" + "\n---\n".join(mini_summaries)


        print(f"[Map-Reduce] Final Aggregation (Size: {len(final_input)} chars)")


        try:
             final_report = llm_summarise(final_input, author, date, end, total_file, total_add, total_del)
             if final_report: return final_report
        except Exception:
             pass


        try:
             if len(final_input) > 8000:


                  splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=500)
                  agg_chunks = splitter.create_documents([final_input])
                  agg_res = []
                  for ac in agg_chunks:
                       agg_res.append(llm_summarise_hf(ac.page_content, author, date, end, total_file, total_add, total_del) or "")
                  return "\n".join(agg_res)
             else:
                  final_report = llm_summarise_hf(final_input, author, date, end, total_file, total_add, total_del)
                  if final_report: return final_report
        except Exception:
             pass


        try:
             final_report = llm_summarise_activity_groq(final_input, author, date, end, total_file, total_add, total_del)
             if final_report: return final_report
        except Exception:
             pass

        return None

    except Exception as e:
        print(f"\n--- Map-Reduce Summarization Failed ---")
        print(f"Error: {e}")
        return None

def llm_summarise_activity_groq(activity_text, author, date=None, end=None, total_file=None, total_add=None, total_del=None):

  if date is None:
    date = datetime.now().date()
  if end is None:
    end = date


    system_prompt =  f"""
    You are an assistant with a tech background.
    Your job is to create a report on the changes made in a Git repository.
    Summarize the content of the changes over the specified duration.
    Format the output as a structured report.
    Moreover, you should mention the name of the contributor {author} and the date of which the report from {date} to {end} generated.
    Provide without any emoji or any other special symbols like hashtags.
    Arrange and do organise the content in a proper manner professional report manner.
    Include a section titled 'Chronological Activity Timeline' that lists the key changes mapped to their specific dates
    At the start of the report include the total number of files {total_file} changed, total number of additions {total_add} and total number of deletions {total_del}.
    """

    try:
        client = Groq(
            api_key= os.getenv('GROQ_TOKEN'),
        )

        chat_completion = client.chat.completions.create(
            messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": activity_text,
            }
        ],
        model="llama3-70b-8192",
    )

        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"\n--- AI Summarization Failed ---")
        print(f"Error: {e}")
        print("Note: Ensure your GOOGLE_API_KEY is correct and you have quota available.")


def summary_to_mail(to_email, sender_email, sender_pwd, summary_text):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = 'Git Repo Summary Report, straight from the AI Agent'
    msg.attach(MIMEText(summary_text, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, sender_pwd)
    server.sendmail(sender_email, to_email, msg.as_string())
    server.quit()


def smart_summary_fallback(text, author, start_date = None, end_date = None, total_file = None, total_add = None, total_del = None):
    if start_date is None:
        start_date = datetime.now().date()
    if end_date is None:
        end_date = start_date

    try:
        print(f"\n   [Hybrid-FallBack] Gemini (primary): ")
        report = llm_summarise(text, author, start_date, end_date, total_file, total_add, total_del)
        if report and len(report.strip()) > 10:
            print(f"   [Success] Gemini (primary)")
            return report
    except Exception as e:
        print(f"   [Warning] Gemini failed ({e}). Switching to Secondary...")


    try:
        print(f"\n   [Hybrid-FallBack] HuggingFace (secondary): ")

        SAFE_HF_LIMIT = 8000

        if len(text) > SAFE_HF_LIMIT:
            print(f"   [Logic] Text length {len(text)} exceeds safe HF limit ({SAFE_HF_LIMIT}). Splitting dynamically...")

            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=SAFE_HF_LIMIT,
                chunk_overlap=500,
                separators=["\nCOMMIT:", "\n", " "]
            )
            sub_chunks = fallback_splitter.create_documents([text])

            sub_summaries = []
            for i, sub_chunk in enumerate(sub_chunks):
                print(f"     -> Processing sub-chunk {i+1}/{len(sub_chunks)} via HuggingFace...")
                sub_res = llm_summarise_hf(sub_chunk.page_content, author, start_date, end_date, total_file, total_add, total_del)
                if sub_res:
                    sub_summaries.append(sub_res)

            combined_text = "\n".join(sub_summaries)
            if len(combined_text) < SAFE_HF_LIMIT:
                 return llm_summarise_hf(combined_text, author, start_date, end_date, total_file, total_add, total_del)
            else:
                 return combined_text

        else:
            report = llm_summarise_hf(text, author, start_date, end_date, total_file, total_add, total_del)
            if report and len(report.strip()) > 10:
                print(f"   [Success] HuggingFace (secondary)")
                return report

    except Exception as e:
        print(f"   [Warning] HuggingFace failed ({e}). Switching to Tertiary...")


    try:
        print(f"\n   [Hybrid-FallBack] Groq (tertiary): ")
        report = llm_summarise_activity_groq(text, author, start_date, end_date, total_file, total_add, total_del)
        if report and len(report.strip()) > 10:
            print(f"   [Success] Groq (tertiary)")
            return report
    except Exception as e:
        print(f"   [Error] Groq failed ({e}).")

    print(f"\n   [Failure] All LLM agents failed for this chunk.")
    return None


def smart_MapReduce_fallback(activity_text_list, author, start_date=None, end_date=None, total_file=None, total_add=None, total_del=None):

    print(f"\n[Smart Map-Reduce] Initiating protocol for heavy payload...")
    try:
        report = map_reduce_summarise(
            activity_text_list,
            author,
            start_date,
            end_date,
            chunk=200000,
            total_file=total_file,
            total_add=total_add,
            total_del=total_del
        )
        return report
    except Exception as e:
        print(f"[Smart Map-Reduce] Large chunk strategy failed ({e}). Retrying with Conservative Strategy...")

        try:
             report = map_reduce_summarise(
                activity_text_list,
                author,
                start_date,
                end_date,
                chunk=8000,
                total_file=total_file,
                total_add=total_add,
                total_del=total_del
            )
             return report
        except Exception as e2:
             print(f"[Critical] All Map-Reduce strategies failed: {e2}")
             return None


def run_analytics(repo_list_path: str, since: datetime, until: datetime, author: str = None):
    agent = GitAgent()
    # Determine whether the argument is a file path or a raw URL
    if os.path.isfile(repo_list_path):
        repos = agent.load_repo_list(file_path)
    else:
        # Assume a single repository URL was provided
        repos = [repo_list_path]
    all_stats = []
    for url in repos:
        print(f"[INFO] Processing repository: {url}")
        repo_stats = agent.fetch_repo_stats(url, since, until, author)
        all_stats.append(repo_stats)
    # 2. Aggregate to DataFrame
    df = agent.aggregate_to_dataframe(all_stats)

    # 3. Churn analysis (saves churn_analysis.csv)
    agent.compute_churn(df)

    print("[SUCCESS] Multi-repo analytics complete. Data stored in repo_stats.csv and churn_analysis.csv")

def main():

    token = os.getenv('token')

    agent = GitAgent(token=token)

    ''' user_ = input("[INPUT] Enter GitHub username: ")
    repo_ = input("[INPUT] Enter GitHub repository: ") '''


    repo_url = f"https://github.com/khyati-2025/React-Roadmap.git"

    print(f"[Connecting]  {repo_url} ")
    try:
        details = agent.connect(repo_url)
        print(f"Connected to: {details['full_name']}")
        print(f"Permissions: Read={details['permissions']['read']} Write={details['permissions']['write']}\n")
        start = datetime(2025, 7, 5)
        end = datetime(2025, 12, 26)

        ''' start_date = input("[INPUT] Enter start date (YYYY-MM-DD): ")
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = input("[INPUT] Enter end date (YYYY-MM-DD): ")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            raise ValueError("Start date must be before end date")
        elif end == None:
            temp = start.day + 1
            end = start.replace(day=temp)
        elif start == end:
            temp = end.day + 1
            end = end.replace(day=temp)

        author = input("[INPUT] Enter author/contributer (i.e. username) name to filler or leave empty: ")
        if author == "":
            author = None

        mail_add = input("[INPUT] Enter the sender's email address: ")
        if mail_add == "":
            mail_add = "kkmistry936@gmail.com"


        r = input("[INPUT] Want to run analytics? (y/n): ")
        if r == "y":
            run_analytics(repo_url, start, end, author)
            print("[INFO] Exiting after analytics run to avoid duplicate summarization.")
            return # Exit immediately as requested to avoid second summarization '''

        author = None
        print(f"[Fetching] commits for {author or 'all contributors'}...")
        commits = agent.get_commits(since=start, until=end, author=author)


        stats = agent.get_statistics(commits)

        if stats['total_commits'] > 0:

            print("[Fetching] Commit Details")

            activity_summary = []
            for commit in commits:
                data = agent.parse_commit_data(commit)
                if not data: continue

                commit_text = f"Commit: {data['timestamp']} -> {data['message'].strip()}\n"
                for f in data['file_details']:

                    if "node_modules" in f['filename'].lower() or f['filename'].endswith('.map'):
                        continue

                    commit_text += f"File {f['filename']}: {f['status']}\n"
                    if f['patch']:
                        patch_text = f['patch']
                        if len(patch_text) > 400:
                            patch_text = patch_text[:400] + "\n... [Code Truncated] ..."
                        commit_text += f"Changes:\n{patch_text}\n"
                activity_summary.append(commit_text)

                print(f"\nCOMMIT: {data['hash'][:8]}")
                print(f"Author: {data['author']} <{data['email']}>")

                print(f"Date:   {data['timestamp']}")
                print(f"Message: {data['message'].strip()}")
                print("-" * 20)

                """  for f in data['file_details']:
                    print(f"FILE: {f['filename']} ({f['status']})")
                    if f['patch']:
                        print("CODE CHANGES:")
                        print(f['patch'])
                    else:
                        print("CODE CHANGES: [No patch/binary file]")
                    print("-" * 10)
                print("\n" + "~"*50) """

            print("\n[Summary Statistics]")
            print(f"Total Commits: {stats['total_commits']}")
            print(f"Total Contributors: {stats['total_contributors']}")
            print(f"Total Files Changed: {stats['total_files_changed']}")
            total_file = stats['total_files_changed']
            total_add = stats['total_additions']
            total_del = stats['total_deletions']
            print(f"Total Additions: {stats['total_additions']}")
            print(f"Total Deletions: {stats['total_deletions']}")

            print("\n[Overview]")
            for author, s in stats['per_contributor'].items():
                print(f"{author}: {s['commits']} commits, +{s['additions']} / -{s['deletions']}")


            print("\n[Generating Report]")
            full_text = "\n".join(activity_summary)
            char_count = len(full_text)

            author=None
            if author == None:
                main_author = list(stats['per_contributor'].keys())[0] if stats['per_contributor'] else "Unknown"
            else:
                main_author = author

            print(f"\n[System] Payload Size: {char_count} characters.")

            if char_count > 600000:
                print("\n[Payload Too Large]")
                print(f"Warning: Even with truncation, the text ({char_count} chars) exceeds safe AI limits.")
                print("\n[Partial AI Summarization (Map-Reduce)]")

                partial_report = smart_MapReduce_fallback(activity_summary, main_author, start.date(), end.date(),  total_file, total_add, total_del)
                if partial_report:
                    print(partial_report)
                    with open("summaryPartial.txt", "w", encoding="utf-8") as f:
                        f.write(partial_report)
                    print("\n[Success] Deep-Summary saved to summary.txt")

            else:

                try:


                    report = smart_summary_fallback(full_text, main_author, start.date() , end.date(),total_file, total_add, total_del) # Corrected: Pass full_text string

                    if report:
                        with open("summary100.txt", "w", encoding="utf-8") as f:
                            f.write(report)

                        email = mail_add
                        from_ = "khyatimistry2025@gmail.com"
                        pwd = os.getenv("pwd")
                        summary_to_mail(email, from_, pwd, report)
                        print(f"\n[Success] Report saved to summary100.txt and send to this mail address {email} from {from_}")
                    else:
                        raise ValueError("Empty response from AI Agent")

                finally:
                    print("\n[END OF SCRIPT]")


                    ''' model =  "microsoft/Phi-3.5-mini-instruct"
                   report = llm_speed_hf(full_text, main_author, start.date(), end.date())
                   print(report) '''




                    """ print("\n--- AI Summarization using Gemini ---")
                    report = llm_summarise(full_text, main_author, start.date())

                    if report:

                        with open("summary.txt", "w", encoding="utf-8") as f:
                            f.write(report)
                        ''' email = "kkmistry936@gmail.com"
                        from_ = "khyatimistry2025@gmail.com"
                        pwd = "fxov gkzv hceo nojg"
                        summary_to_mail(email, from_, pwd, report)
                        print(f"\n[Success] Report saved to summary.txt and send to this mail address {email} from {from_}") '''

                    else:
                        raise ValueError("Empty response from Gemini")

                except Exception as e:
                    print(f"\n[Warning] Gemini failed ({e}). Switching to Fallback...")

                    try:

                        print("--- AI Summarization using HuggingFace (Fallback) ---")
                        report = llm_summarise_hf(full_text, main_author, start.date())
                        if report:
                            with open("summary.txt", "a", encoding="utf-8") as f:
                                f.write(report)

                                ''' email = "kkmistry936@gmail.com"
                                from_ = "khyatimistry2025@gmail.com"
                                pwd = "fxov gkzv hceo nojg"
                                summary_to_mail(email, from_, pwd, report)
                                print(f"\n[Success] Report saved to summary.txt and send to this mail address {email} from {from_}") '''
                        else:
                            raise ValueError("Empty response from HuggingFace")
                    except Exception as e2:
                        print(f"\n[Error] Both AI models failed. Please check your API keys or data size.")
                        try:
                          print("--- AI Summarization using Groq (Fallback) ---")
                          report = llm_summarise_activity_groq(full_text, main_author, start.date())
                          if report:
                            with open("summary.txt", "w", encoding="utf-8") as f:
                                f.write(report)
                                ''' email = "kkmistry936@gmail.com"
                                from_ = "khyatimistry2025@gmail.com"
                                pwd = "fxov gkzv hceo nojg"
                                summary_to_mail(email, from_, pwd, report)
                                print(f"\n[Success] Report saved to summary.txt and send to this mail address {email} from {from_}") '''

                          else:
                              raise ValueError("Empty response from HuggingFace")

                        except Exception as e3:
                            print(f"\n[Error] All the AI models failed. Please check your API keys or data size.") """








        else:
            print("\nNo commits found for the selected period.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()