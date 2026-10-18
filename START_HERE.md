# WattShift — এখান থেকে শুরু করুন

এই package-এ নতুন WattShift project, আসল SMARD data, পাঁচটি Console page, Python backend, Kubernetes configuration, পরীক্ষার রিপোর্ট এবং showcase assets আছে।

1. `README.md` — project কী করে এবং দ্রুত চালানোর পদ্ধতি।
2. `docs/RUNBOOK.md` — local app, cluster ও deployment-এর বিস্তারিত নির্দেশনা।
3. `docs/reviews/final-review.md` — কী বাস্তবে পরীক্ষা হয়েছে, কী এখনো হয়নি।
4. `preview/` — আগে থেকেই build করা Console। এই ফোল্ডারকে static HTTP server দিয়ে খুলতে হবে; index.html double-click করলে data load নাও হতে পারে।
5. `notebooks/01-understand-energy.ipynb` — data ও হিসাব বোঝার ছোট notebook।
6. `docs/assets/evidence-walkthrough.mp4` — প্রায় দুই মিনিটের ফলাফল ও স্থানীয় পরীক্ষার walkthrough। এটি live cluster-এর recording নয়।
7. `legacy/wattshift-prototype.zip` — আগের কাজের সংরক্ষিত কপি, পরিবর্তন করা হয়নি।

**RC3 আপডেট:** Kueue `AdmissionCheck` দিয়ে job-এর প্রথম admission আটকানোর source-level সমাধান যোগ করা হয়েছে। ৮ GB RAM-এর জন্য `make stack-lite` আছে। বাস্তব Kubernetes পরীক্ষা এখনো বাকি। `docs/reviews/rc3-admission-audit.md` দেখুন।

**যা পুরোপুরি শেষ হয়নি:** বাস্তব Kubernetes acceptance, browser visual review, GitHub Pages/release প্রকাশ, live Grafana screenshot/interaction video এবং আসল GPU measurement। এই environment-এ প্রয়োজনীয় runtime/GPU নেই; GitHub-এর লক্ষ্য repository-ও নির্ধারিত নেই। এগুলোকে সম্পন্ন বলে দেখানো হয়নি। Live Jobs event-history/Gantt ও always-on inference demo-ও পরবর্তী কাজের তালিকায় আছে।

**ফলাফল:** নির্দিষ্ট এক সপ্তাহের ৪৮টি simulated job-এ forecast policy energy cost ৭.৭৮% কমিয়েছে। এটি GPU rental bill-এর সাশ্রয় নয়। Carbon-এর ফল আলাদা করে report-এ আছে; সব policy carbon কমায়নি।

Git history প্রয়োজন হলে `git clone wattshift-history.bundle restored-source` ব্যবহার করুন। Bundle-এ source history আছে; বড় legacy archive ও prebuilt preview ZIP-এর আলাদা অংশ হিসেবে দেওয়া হয়েছে।

**RC4 যাচাই:** `docs/reviews/rc4-preflight.md` ফাইলে স্বাধীন source review, সংশোধন এবং অসম্পন্ন live-test তালিকা আছে।
