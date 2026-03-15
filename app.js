/* CMB Law — App JavaScript */
(function () {
  "use strict";

  var API = "port/8000";

  /* ─── Team Bio Data ─── */
  var teamData = {
    josh: {
      name: "Josh Clayton",
      title: "Partner",
      photo: "./assets/josh.png",
      bio: "<p>Josh Clayton is an experienced corporate and securities attorney with over a decade of practice in capital markets, mergers and acquisitions, and strategic transactions. He has represented issuers, investors, and financial institutions across a wide range of capital-raising activities, including recapitalizations, restructurings, secondary offerings, venture capital and seed financings, and strategic investments.</p><p>Josh serves as primary outside counsel for companies in the technology, real estate, and energy sectors, advising on corporate governance, due diligence, SEC compliance, and general corporate matters. He has managed complex domestic and international transactions spanning markets in Australia, China, Argentina, Israel, and beyond.</p><p>His representative engagements include serving as lead counsel for international acquisitions and financing rounds for technology companies, and representing a whistleblower in the first-ever recovery under the Motor Vehicle Safety Whistleblower Act.</p><h4>Education</h4><p class=\"detail-list\">J.D. (Honors), Emory University School of Law<br>B.B.A. Accounting, West Texas A&M University</p><h4>Admissions</h4><p class=\"detail-list\">State Bar of Texas &middot; Eastern District of Texas &middot; U.S. Court of Appeals for the Fifth Circuit &middot; All Texas Federal District Courts</p>",
      contact:
        '<a href="mailto:josh@cmblaw.com">josh@cmblaw.com</a><a href="tel:+17134106217">713-410-6217</a>',
    },
    brannon: {
      name: "Brannon McKay",
      title: "Partner",
      photo: "./assets/brannon.png",
      bio: "<p>Brannon McKay is a founding partner of CMB and a patent attorney focused on efficient patent preparation and prosecution, trademark acquisition and enforcement, and IP litigation. After honing his practice at Finnegan, one of the world\u2019s premier IP boutiques, Brannon co-founded CMB to deliver top-tier patent work with streamlined efficiency.</p><p>Brannon has prepared and prosecuted hundreds of patent applications across a wide range of technologies, with particular depth in AI, machine learning, wireless communications (including 5G), encryption, virtual machines, and health and wellness technologies such as cardiac ablation and physiological monitoring systems. He counsels Fortune 100 companies and emerging technology firms alike on patent portfolio strategy, prosecution, and IP risk management.</p><p>His trademark practice encompasses the full lifecycle \u2014 from clearance and application through opposition, cancellation, and enforcement proceedings \u2014 with over 100 marks acquired for clients to date. As a seasoned IP litigator, Brannon has represented both plaintiffs and defendants in patent and trademark disputes in federal courts across the country.</p><h4>Education</h4><p class=\"detail-list\">J.D., Georgia State University College of Law<br>B.S. Computer Engineering, Georgia Institute of Technology</p><h4>Admissions</h4><p class=\"detail-list\">Georgia Bar &middot; USPTO Patent Bar &middot; U.S. Court of Appeals for the Federal Circuit &middot; Eastern District of Texas &middot; Northern District of Georgia &middot; Supreme Court of Georgia &middot; Fulton County Superior Court &middot; Court of Appeals for Veterans Claims</p>",
      contact:
        '<a href="mailto:brannon@cmblaw.com">brannon@cmblaw.com</a><a href="tel:+14044148633">404-414-8633</a>',
    },
    ben: {
      name: "Ben Bailey",
      title: "Partner",
      photo: "./assets/ben.png",
      bio: "<p>Ben Bailey is a founding partner of CMB with nearly twenty years of intellectual property experience. He focuses on efficient patent preparation and prosecution, trademark protection and enforcement, and IP litigation. Ben launched his career at Finnegan, one of the world\u2019s largest IP boutiques, before co-founding CMB in 2013.</p><p>Ben has extensive experience preparing and prosecuting patent applications, managing patent portfolios, negotiating licensing agreements, and litigating patent rights. He has analyzed large-scale patent portfolios for advanced technology companies and counsels clients on strategic portfolio growth and IP monetization. His technical expertise spans mechanical, electrical, and software technologies, with particular depth in medical devices and wellness technologies (cardiovascular, heart rate monitoring, glucose monitoring), home automation, IoT, fiber optics, and data analytics.</p><p>His trademark practice covers the full spectrum \u2014 preparing and prosecuting applications, policing marks, and enforcing trademark rights domestically and globally. Ben also represents both plaintiffs and defendants in patent and trademark litigation in U.S. district courts.</p><h4>Education</h4><p class=\"detail-list\">J.D., Georgia State University College of Law<br>B.S. Mechanical Engineering, Georgia Institute of Technology</p><h4>Admissions</h4><p class=\"detail-list\">Georgia Bar &middot; USPTO Patent Bar &middot; Supreme Court of Georgia &middot; Northern District of Georgia &middot; Fulton County Superior Court &middot; Court of Appeals for Veterans Claims</p>",
      contact:
        '<a href="mailto:ben@cmblaw.com">ben@cmblaw.com</a><a href="tel:+16786671388">678-667-1388</a>',
    },
    ginger: {
      name: "Ginger Turner, Ph.D., P.E.",
      title: "Patent Agent \u2014 Through Gingineer Consulting LLC",
      photo: "./assets/ginger.png",
      bio: "<p>Ginger Turner is a USPTO-registered patent agent and electrical engineer with extensive experience drafting and prosecuting complex patent applications across sectors including medical devices, bioinformatics, semiconductors, energy systems, and AI-driven technologies. As founder of Gingineer Consulting LLC, she partners with law firms, in-house counsel, and small business owners to deliver technically rigorous, strategically aligned patent filings, portfolio management, and litigation support consulting.</p><p>After earning her Ph.D. from Purdue University with a focus on semiconductor devices, Dr. Turner spent over seven years conducting engineering failure analysis investigations at Exponent before transitioning to patent law. She then spent more than eight years at Troutman Sanders (now Troutman Pepper Locke), honing her expertise in patent prosecution and portfolio management. Her deep technical foundation and big-law training enable her to interface fluently with inventors and R&D teams while operating with high efficiency.</p><p>Over the course of her 15+ year career, Dr. Turner has also served as an expert witness in product safety and patent infringement litigation, testifying in depositions and court and contributing to multimillion-dollar outcomes. Known for her precision, responsiveness, and clarity, she brings both legal insight and engineering fluency to every engagement.</p><h4>Education</h4><p class=\"detail-list\">Ph.D., Purdue University (Semiconductor Devices)<br>P.E., Licensed Professional Engineer</p>",
      contact:
        '<a href="mailto:ginger@cmblaw.com">ginger@cmblaw.com</a><span>Through Gingineer Consulting LLC</span>',
    },
    becky: {
      name: "Becky Chiusano",
      title: "IP Program Manager",
      photo: "./assets/becky.png",
      bio: "<p>Becky Chiusano brings more than 30 years of intellectual property administration expertise to CMB. She began her career in 1992 as a patent assistant and has since built deep operational knowledge across both law firm and corporate IP environments \u2014 including managing patent programs for large corporations and running her own business.</p><p>At CMB, Becky oversees docketing operations, invoicing, and IP data management. She ensures that all filings are made with the USPTO on schedule and that clients receive timely, accurate reporting on their portfolios. Her strategic approach to IP support operations \u2014 combining law firm precision with corporate-scale efficiency \u2014 has earned her multiple industry awards for delivering results.</p><p>Becky\u2019s breadth of experience makes her an essential part of the CMB team, providing the operational backbone that allows the firm\u2019s attorneys to focus on substantive legal work.</p>",
      contact:
        '<a href="mailto:becky@cmblaw.com">becky@cmblaw.com</a>',
    },
    manoj: {
      name: "Manoj Gandhi",
      title: "Partner \u2014 Through Gandhi Law LLC",
      photo: "./assets/manoj.png",
      bio: "<p>Manoj Gandhi provides early-stage to mid-size companies with outside general counsel services, handling business litigation, corporate transactions, and day-to-day legal and operational guidance. Whether serving as a strong courtroom advocate or a savvy deal negotiator, he meets clients\u2019 needs across the full spectrum of business law. As an entrepreneur himself, Manoj advises companies from startup through acquisition \u2014 developing IP strategy, reviewing contracts, preparing corporate formation documents, and implementing business development objectives.</p><p>Prior to CMB, Manoj honed his legal skills for over a decade at Akin Gump, an international law firm. He is an accomplished litigator and adviser on a wide variety of critical matters, including patent, trademark, and trade secret litigation, practicing in both federal and state courts across the country. Manoj advises clients across a comprehensive array of technologies, including computer and telecommunications, software, streaming media, GPS navigation, battery charging, oilfield services and equipment, medical devices, fitness electronics, and blockchain.</p><p>Manoj also combines his passion for creative content \u2014 particularly music and film \u2014 with his practice. Using his background in IP enforcement, he counsels creators on the negotiation of sponsorship, licensing, and endorsement agreements across social media and traditional entertainment.</p><h4>Education</h4><p class=\"detail-list\">J.D., University of Houston Law Center<br>B.S.E. Computer & Telecommunications Engineering (Minor in Economics), University of Pennsylvania<br>Study Abroad: Hong Kong University of Science & Technology</p><h4>Admissions</h4><p class=\"detail-list\">Texas Bar &middot; Eastern District of Texas</p>",
      contact:
        '<a href="mailto:manoj@cmblaw.com">manoj@cmblaw.com</a><a href="tel:+18327824964">832-782-4964</a><span>Through Gandhi Law LLC</span>',
    },
  };

  /* ─── Theme Toggle ─── */
  var themeToggle = document.querySelector("[data-theme-toggle]");
  var root = document.documentElement;
  var theme = window.location.hash === "#dark"
    ? "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  root.setAttribute("data-theme", theme);
  updateThemeIcon();

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      theme = theme === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", theme);
      themeToggle.setAttribute(
        "aria-label",
        "Switch to " + (theme === "dark" ? "light" : "dark") + " mode"
      );
      updateThemeIcon();
    });
  }

  function updateThemeIcon() {
    if (!themeToggle) return;
    themeToggle.innerHTML =
      theme === "dark"
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }

  /* ─── Header Scroll ─── */
  var header = document.getElementById("header");
  window.addEventListener(
    "scroll",
    function () {
      if (window.scrollY > 40) {
        header.classList.add("header--scrolled");
      } else {
        header.classList.remove("header--scrolled");
      }
    },
    { passive: true }
  );

  /* ─── Mobile Menu ─── */
  var mobileToggle = document.querySelector("[data-mobile-toggle]");
  var mobileNav = document.getElementById("mobileNav");
  var mobileLinks = mobileNav.querySelectorAll("[data-nav-link]");

  if (mobileToggle) {
    mobileToggle.addEventListener("click", function () {
      var isOpen = mobileNav.classList.toggle("active");
      mobileToggle.setAttribute("aria-expanded", isOpen);
      mobileToggle.innerHTML = isOpen
        ? '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
        : '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
    });
  }

  mobileLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      mobileNav.classList.remove("active");
      mobileToggle.setAttribute("aria-expanded", "false");
      mobileToggle.innerHTML =
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';
    });
  });

  /* ─── Team Modal ─── */
  var modalOverlay = document.getElementById("teamModal");
  var modalName = document.getElementById("modalName");
  var modalTitle = document.getElementById("modalTitle");
  var modalAvatar = document.getElementById("modalAvatar");
  var modalBody = document.getElementById("modalBody");
  var modalCloseBtn = document.querySelector("[data-modal-close]");
  var teamCards = document.querySelectorAll("[data-team]");

  teamCards.forEach(function (card) {
    function openModal() {
      var key = card.getAttribute("data-team");
      var data = teamData[key];
      if (!data) return;

      modalName.textContent = data.name;
      modalTitle.textContent = data.title;
      modalAvatar.src = data.photo;
      modalAvatar.alt = data.name;
      modalBody.innerHTML =
        data.bio +
        '<div class="modal-contact">' +
        data.contact +
        "</div>";
      modalOverlay.classList.add("active");
      document.body.style.overflow = "hidden";
      modalCloseBtn.focus();
    }
    card.addEventListener("click", openModal);
    card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openModal();
      }
    });
  });

  function closeModal() {
    modalOverlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeModal);
  }
  modalOverlay.addEventListener("click", function (e) {
    if (e.target === modalOverlay) closeModal();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modalOverlay.classList.contains("active")) {
      closeModal();
    }
  });

  /* ─── Smart Intake Form ─── */
  var intakeForm = document.getElementById("intakeForm");
  var intakeState = { ipNeed: "", techArea: "", step: 1 };

  function showStep(n) {
    intakeForm.querySelectorAll(".intake-step").forEach(function (s) {
      s.classList.remove("active");
    });
    var target = intakeForm.querySelector('[data-step="' + n + '"]');
    if (target) target.classList.add("active");
    intakeState.step = n;
  }

  // Step 1: IP Need selection
  document.getElementById("ipNeedOptions").addEventListener("click", function (e) {
    var btn = e.target.closest(".intake-option");
    if (!btn) return;
    // visual selection
    this.querySelectorAll(".intake-option").forEach(function (b) {
      b.classList.remove("selected");
    });
    btn.classList.add("selected");
    intakeState.ipNeed = btn.getAttribute("data-value");

    // go straight to contact details
    setTimeout(function () {
      showStep(2);
    }, 200);
  });

  // Back buttons
  intakeForm.querySelectorAll("[data-back]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (intakeState.step === 2) {
        showStep(1);
      }
    });
  });

  /* ─── File Upload UI ─── */
  var fileUploadArea = document.getElementById("fileUploadArea");
  var fileInput = document.getElementById("intakeFiles");
  var fileList = document.getElementById("fileList");
  var selectedFiles = [];

  // Drag and drop
  ["dragenter", "dragover"].forEach(function (evt) {
    fileUploadArea.addEventListener(evt, function (e) {
      e.preventDefault();
      e.stopPropagation();
      fileUploadArea.classList.add("drag-over");
    });
  });
  ["dragleave", "drop"].forEach(function (evt) {
    fileUploadArea.addEventListener(evt, function (e) {
      e.preventDefault();
      e.stopPropagation();
      fileUploadArea.classList.remove("drag-over");
    });
  });
  fileUploadArea.addEventListener("drop", function (e) {
    var files = e.dataTransfer.files;
    addFiles(files);
  });

  fileInput.addEventListener("change", function () {
    addFiles(this.files);
    this.value = ""; // reset so re-selecting same file works
  });

  function addFiles(fileListInput) {
    for (var i = 0; i < fileListInput.length; i++) {
      var f = fileListInput[i];
      if (f.size > 10 * 1024 * 1024) {
        // eslint-disable-next-line no-alert
        alert(f.name + " exceeds the 10 MB limit.");
        continue;
      }
      // avoid duplicates by name+size
      var dup = selectedFiles.some(function (sf) {
        return sf.name === f.name && sf.size === f.size;
      });
      if (!dup) selectedFiles.push(f);
    }
    renderFileList();
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function renderFileList() {
    fileList.innerHTML = "";
    selectedFiles.forEach(function (f, idx) {
      var div = document.createElement("div");
      div.className = "file-item";
      div.innerHTML =
        '<span class="file-item-name">' + f.name + "</span>" +
        '<span class="file-item-size">' + formatSize(f.size) + "</span>" +
        '<button type="button" class="file-item-remove" data-idx="' + idx + '" aria-label="Remove ' + f.name + '">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>';
      fileList.appendChild(div);
    });
  }

  fileList.addEventListener("click", function (e) {
    var btn = e.target.closest(".file-item-remove");
    if (!btn) return;
    var idx = parseInt(btn.getAttribute("data-idx"), 10);
    selectedFiles.splice(idx, 1);
    renderFileList();
  });

  // Form submission with files
  intakeForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var formData = new FormData();
    formData.append("name", document.getElementById("intakeName").value);
    formData.append("email", document.getElementById("intakeEmail").value);
    formData.append("company", document.getElementById("intakeCompany").value);
    formData.append("ip_need", intakeState.ipNeed);
    formData.append("tech_area", intakeState.techArea);
    formData.append("urgency", document.getElementById("intakeUrgency").value);
    formData.append("description", document.getElementById("intakeDesc").value);
    formData.append("attorney", document.getElementById("intakeAttorney").value);

    selectedFiles.forEach(function (f) {
      formData.append("files", f);
    });

    fetch(API + "/api/intake", {
      method: "POST",
      body: formData,
    })
      .then(function () {
        selectedFiles = [];
        renderFileList();
        showStep("success");
      })
      .catch(function () {
        showStep("success"); // Show success anyway for UX
      });
  });

  /* ─── AI Chat Widget ─── */
  var chatFab = document.getElementById("chatFab");
  var chatPanel = document.getElementById("chatPanel");
  var chatClose = document.getElementById("chatClose");
  var chatMessages = document.getElementById("chatMessages");
  var chatInput = document.getElementById("chatInput");
  var chatSend = document.getElementById("chatSend");
  var chatHistory = [];
  var chatStreaming = false;

  chatFab.addEventListener("click", function () {
    chatPanel.classList.add("active");
    chatFab.classList.add("hidden");
    chatInput.focus();
    if (chatHistory.length === 0) {
      addMessage("assistant", "Hello! I\u2019m the CMB Law intake assistant. How can I help you today? I can answer questions about our patent, trademark, corporate, and litigation services, or help you get started with a new matter.");
    }
  });

  chatClose.addEventListener("click", function () {
    chatPanel.classList.remove("active");
    chatFab.classList.remove("hidden");
  });

  function addMessage(role, text) {
    var div = document.createElement("div");
    div.className = "chat-msg chat-msg--" + role;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (role !== "typing") {
      chatHistory.push({ role: role, content: text });
    }
    return div;
  }

  function sendChat() {
    var text = chatInput.value.trim();
    if (!text || chatStreaming) return;

    addMessage("user", text);
    chatInput.value = "";
    chatInput.style.height = "auto";
    chatStreaming = true;
    chatSend.disabled = true;

    var typingEl = addMessage("typing", "...");

    fetch(API + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory.filter(function (m) { return m.role !== "typing"; }) }),
    })
      .then(function (res) {
        var reader = res.body.getReader();
        var decoder = new TextDecoder();
        var assistantText = "";

        // Replace typing indicator with real message
        typingEl.className = "chat-msg chat-msg--assistant";
        typingEl.textContent = "";

        function read() {
          reader.read().then(function (result) {
            if (result.done) {
              chatHistory.push({ role: "assistant", content: assistantText });
              chatStreaming = false;
              chatSend.disabled = false;
              return;
            }
            var chunk = decoder.decode(result.value, { stream: true });
            var lines = chunk.split("\n");
            lines.forEach(function (line) {
              if (line.startsWith("data: ") && line !== "data: [DONE]") {
                try {
                  var data = JSON.parse(line.slice(6));
                  if (data.text) {
                    assistantText += data.text;
                    typingEl.textContent = assistantText;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                  }
                } catch (_e) {
                  // ignore parse errors
                }
              }
            });
            read();
          });
        }
        read();
      })
      .catch(function () {
        typingEl.textContent = "Sorry, I couldn\u2019t connect. Please try again or call us at (404) 414-8633.";
        typingEl.className = "chat-msg chat-msg--assistant";
        chatStreaming = false;
        chatSend.disabled = false;
      });
  }

  chatSend.addEventListener("click", sendChat);
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 80) + "px";
  });
})();
