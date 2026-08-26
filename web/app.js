// State Variables
let activeDate = new Date().toISOString().split("T")[0];
let currentCurrency = "PKR ";
let activeEntryType = "Expense"; // "Expense", "Credit", "Udhaar", "UdhaarReturned"
let activeSelectedMonth = "";
let khataClientsList = [];
let staffMembersList = [];

// =============================================================================
// AUTHENTICATION & PIN PROTECTION
// =============================================================================
function isSessionAuthenticated() {
    return sessionStorage.getItem("rion_auth_token") === "rion_auth_session_valid";
}

function checkAuthOnLoad() {
    const overlay = document.getElementById("login-overlay");
    if (isSessionAuthenticated()) {
        if (overlay) overlay.classList.add("hidden");
    } else {
        if (overlay) {
            overlay.classList.remove("hidden");
            const pinIn = document.getElementById("loginPinInput");
            if (pinIn) pinIn.focus();
        }
    }
}

async function handleWebLogin(e) {
    if (e) e.preventDefault();
    const pinIn = document.getElementById("loginPinInput");
    const errEl = document.getElementById("loginErrorMsg");
    const btn = document.getElementById("loginSubmitBtn");
    const pin = pinIn?.value.trim() || "";

    if (!pin) return;

    if (btn) btn.disabled = true;
    if (errEl) errEl.classList.add("hidden");

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin: pin })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Invalid Security PIN");
        }

        const data = await res.json();
        sessionStorage.setItem("rion_auth_token", data.token || "rion_auth_session_valid");
        
        const overlay = document.getElementById("login-overlay");
        if (overlay) overlay.classList.add("hidden");
        if (pinIn) pinIn.value = "";
    } catch (e) {
        if (errEl) {
            errEl.textContent = e.message || "Invalid PIN. Please try again.";
            errEl.classList.remove("hidden");
        }
        if (pinIn) {
            pinIn.value = "";
            pinIn.focus();
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function handleBiometricWebLogin() {
    const errEl = document.getElementById("loginErrorMsg");
    if (!window.PublicKeyCredential) {
        alert("Face ID / Biometrics is not supported on this browser.");
        return;
    }

    try {
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        if (!available) {
            alert("Biometrics / Touch ID / Face ID hardware is not available on this device.");
            return;
        }

        const savedBioPin = localStorage.getItem("rion_bio_pin");
        if (!savedBioPin) {
            // First-time biometric registration
            let promptPin = document.getElementById("loginPinInput")?.value.trim();
            if (!promptPin) {
                promptPin = prompt("🔑 Enter your Security PIN to link Face ID / Biometrics on this device:");
            }
            if (!promptPin) return;

            // Verify with backend
            const verifyRes = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin: promptPin })
            });
            if (!verifyRes.ok) {
                alert("❌ Invalid PIN. Biometrics not linked.");
                return;
            }

            // Register WebAuthn credential (triggers native Face ID / Touch ID enrollment prompt)
            const challenge = new Uint8Array(32);
            window.crypto.getRandomValues(challenge);
            const userId = new Uint8Array(16);
            window.crypto.getRandomValues(userId);

            const cred = await navigator.credentials.create({
                publicKey: {
                    challenge: challenge,
                    rp: { name: "Rion Snooker Lounge" },
                    user: {
                        id: userId,
                        name: "rion_admin",
                        displayName: "Rion Administrator"
                    },
                    pubKeyCredParams: [
                        { alg: -7, type: "public-key" },
                        { alg: -257, type: "public-key" }
                    ],
                    authenticatorSelection: {
                        authenticatorAttachment: "platform",
                        userVerification: "required"
                    },
                    timeout: 60000
                }
            });

            if (cred) {
                localStorage.setItem("rion_bio_pin", promptPin);
                localStorage.setItem("rion_bio_credential_id", btoa(String.fromCharCode(...new Uint8Array(cred.rawId))));
                sessionStorage.setItem("rion_auth_token", "rion_auth_session_valid");
                const overlay = document.getElementById("login-overlay");
                if (overlay) overlay.classList.add("hidden");
                alert("✅ Face ID / Biometrics enabled successfully! You can now use it on every login.");
                return;
            }
        }

        // Trigger the real, physical OS biometric scanner (Face ID / Touch ID / Fingerprint)
        const challenge = new Uint8Array(32);
        window.crypto.getRandomValues(challenge);

        const assertion = await navigator.credentials.get({
            publicKey: {
                challenge: challenge,
                userVerification: "required",
                timeout: 60000
            }
        });

        if (assertion) {
            // Biometric physically confirmed! Log in using verified stored PIN
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin: savedBioPin })
            });

            if (res.ok) {
                const data = await res.json();
                sessionStorage.setItem("rion_auth_token", data.token || "rion_auth_session_valid");
                const overlay = document.getElementById("login-overlay");
                if (overlay) overlay.classList.add("hidden");
                if (errEl) errEl.classList.add("hidden");
            } else {
                localStorage.removeItem("rion_bio_pin");
                localStorage.removeItem("rion_bio_credential_id");
                alert("The Security PIN was changed. Please log in with the new PIN to re-link biometrics.");
            }
        }
    } catch (e) {
        console.warn("Biometric scan cancelled or failed:", e);
        if (errEl) {
            errEl.textContent = "Biometric scan cancelled or not recognized.";
            errEl.classList.remove("hidden");
        }
    }
}

function handleWebLogout() {
    sessionStorage.removeItem("rion_auth_token");
    const overlay = document.getElementById("login-overlay");
    if (overlay) {
        overlay.classList.remove("hidden");
        const pinIn = document.getElementById("loginPinInput");
        if (pinIn) {
            pinIn.value = "";
            pinIn.focus();
        }
    }
}

function toggleLoginPinVisibility() {
    const pinIn = document.getElementById("loginPinInput");
    if (!pinIn) return;
    pinIn.type = pinIn.type === "password" ? "text" : "password";
}

async function handleWebChangePin(e) {
    e.preventDefault();
    const cur = document.getElementById("currentPinInput")?.value.trim();
    const nxt = document.getElementById("newPinInput")?.value.trim();
    const msgEl = document.getElementById("pinStatusMsg");

    if (!cur || !nxt) return;

    try {
        const res = await fetch("/api/auth/change-pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ current_pin: cur, new_pin: nxt })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to update PIN");
        }

        if (msgEl) {
            msgEl.textContent = "✅ Security PIN updated successfully!";
            msgEl.className = "text-xs py-1.5 font-semibold text-emerald-400";
            msgEl.classList.remove("hidden");
        }
        document.getElementById("currentPinInput").value = "";
        document.getElementById("newPinInput").value = "";
    } catch (e) {
        if (msgEl) {
            msgEl.textContent = "❌ " + e.message;
            msgEl.className = "text-xs py-1.5 font-semibold text-rose-400";
            msgEl.classList.remove("hidden");
        }
    }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
    checkAuthOnLoad();
    const dInput = document.getElementById("activeDateInput");
    if (dInput) dInput.value = activeDate;
    
    await loadSettings();
    await refreshDayView();
    await fetchAndPopulateCustomers();
    setupDropzone();
});

async function fetchAndPopulateCustomers() {
    try {
        const res = await fetch("/api/khata");
        if (res.ok) {
            const data = await res.json();
            khataClientsList = data.clients || [];
            populateUploadCustomerSelect();
            const dl = document.getElementById("khataCustomerDatalist");
            if (dl && data.clients) {
                dl.innerHTML = data.clients.map(c => `<option value="${escapeHtml(c.customer_name)}">PKR ${c.pending_balance.toLocaleString()} pending</option>`).join("");
            }
        }
    } catch (e) {
        console.error("Failed to load customers for upload menu:", e);
    }
}

// =============================================================================
// TAB NAVIGATION
// =============================================================================
function switchTab(tabId) {
    const tabs = ["daily", "monthly", "khata", "staff", "history", "chat", "settings"];
    tabs.forEach(t => {
        const sec = document.getElementById(`tab-${t}`);
        const nav = document.getElementById(`nav-${t}`);
        const mob = document.getElementById(`mob-${t}`);

        if (t === tabId) {
            if (sec) sec.classList.remove("hidden");
            if (nav) {
                nav.classList.add("bg-brand-600", "text-white", "shadow");
                nav.classList.remove("text-slate-300", "hover:bg-slate-700/50");
            }
            if (mob) {
                mob.classList.add("text-brand-400", "font-semibold");
                mob.classList.remove("text-slate-400");
            }
        } else {
            if (sec) sec.classList.add("hidden");
            if (nav) {
                nav.classList.remove("bg-brand-600", "text-white", "shadow");
                nav.classList.add("text-slate-300", "hover:bg-slate-700/50");
            }
            if (mob) {
                mob.classList.remove("text-brand-400", "font-semibold");
                mob.classList.add("text-slate-400");
            }
        }
    });

    if (tabId === "daily") refreshDayView();
    if (tabId === "monthly") loadMonthlyClosing();
    if (tabId === "khata") loadKhataSummary();
    if (tabId === "staff") loadStaffSummary();
    if (tabId === "history") loadHistory();
    if (window.lucide) lucide.createIcons();
}

// =============================================================================
// DATE NAVIGATION
// =============================================================================
function onDateChanged(newDate) {
    if (!newDate) return;
    activeDate = newDate;
    refreshDayView();
}

function navigateDay(delta) {
    const d = new Date(activeDate);
    d.setDate(d.getDate() + delta);
    activeDate = d.toISOString().split("T")[0];
    const dInput = document.getElementById("activeDateInput");
    if (dInput) dInput.value = activeDate;
    refreshDayView();
}

function goToToday() {
    activeDate = new Date().toISOString().split("T")[0];
    const dInput = document.getElementById("activeDateInput");
    if (dInput) dInput.value = activeDate;
    refreshDayView();
}

// =============================================================================
// LOAD & REFRESH DAILY VIEW
// =============================================================================
async function refreshDayView() {
    try {
        const res = await fetch(`/api/closings/${activeDate}`);
        if (!res.ok) throw new Error("Failed to fetch day summary");
        const data = await res.json();

        // 6 Financial Settlement Cards
        const cashAmt = data.cash_credit || 0;
        const bankAmt = data.bank_credit || 0;
        const udhaarGivenAmt = data.total_udhaar || 0;
        const udhaarReturnedAmt = data.total_udhaar_returned || 0;
        const expAmt = data.expense_cash || data.total_expense || 0;
        const totalSales = cashAmt + bankAmt;
        const netAmt = totalSales - expAmt;

        setElemText("card-cash", formatMoney(cashAmt));
        setElemText("card-cash-count", `${data.credit_count || 0} cash sales`);

        setElemText("card-bank", formatMoney(bankAmt));
        setElemText("card-bank-count", `${data.slips_count || 0} bank slips`);

        setElemText("card-udhaar", formatMoney(udhaarGivenAmt));
        setElemText("card-udhaar-count", `${data.udhaar_count || 0} given`);

        setElemText("card-udhaar-returned", formatMoney(udhaarReturnedAmt));
        setElemText("card-udhaar-returned-count", `${data.udhaar_returned_count || 0} collected`);

        setElemText("card-expense", formatMoney(expAmt));
        setElemText("card-expense-count", `${data.expense_count || 0} expenses`);

        const netEl = document.getElementById("card-net");
        if (netEl) {
            netEl.textContent = formatMoney(netAmt);
            netEl.className = `text-lg sm:text-xl font-extrabold tracking-tight ${netAmt >= 0 ? "text-brand-300" : "text-rose-400"}`;
        }

        setElemText("footerNetSettlement", `${netAmt >= 0 ? "+" : ""}${formatMoney(netAmt)}`);
        setElemText("activeDateFooterLabel", `Date: ${activeDate}`);

        // Render Day Book Table
        renderDayBook(data.transactions || []);
    } catch (e) {
        console.error("Error refreshing day view:", e);
    }
}

function renderDayBook(txs) {
    const tbody = document.getElementById("daybookTbody");
    const subTitle = document.getElementById("daybookSubtitle");
    if (subTitle) subTitle.textContent = `${txs.length} transactions on this date`;
    if (!tbody) return;

    if (!txs || txs.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" class="p-8 text-center text-slate-500">
              <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
              No entries logged for ${activeDate}. Write an entry or upload slips above!
            </td>
          </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    let rowsHtml = "";
    txs.forEach(t => {
        const isUdhaar = t.tx_type === "Udhaar";
        const isUdhaarRet = t.tx_type === "Udhaar Recovery" || t.category === "Udhaar Recovery";
        const isCredit = t.tx_type === "Credit";
        const isBank = t.payment_method === "Bank" || t.category === "Bank Receipt";
        const isSalary = (t.category || "").includes("Salary") || (t.category || "").includes("Staff");
        
        let typeBadge = "";
        let amtColor = "";
        let amtPrefix = "";

        if (isSalary) {
            typeBadge = `<span class="bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">👨‍💼 SALARY / WAGE</span>`;
            amtColor = "text-rose-400";
            amtPrefix = "-";
        } else if (isUdhaarRet) {
            typeBadge = `<span class="bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">🟣 UDHAAR RET.</span>`;
            amtColor = "text-purple-400";
            amtPrefix = "+";
        } else if (isUdhaar) {
            typeBadge = `<span class="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">🔵 UDHAAR GIVEN</span>`;
            amtColor = "text-indigo-400";
            amtPrefix = "⏳ ";
        } else if (isCredit) {
            typeBadge = isBank 
              ? `<span class="bg-sky-500/20 text-sky-400 border border-sky-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">🏦 BANK IN</span>`
              : `<span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">💵 CASH IN</span>`;
            amtColor = "text-emerald-400";
            amtPrefix = "+";
        } else {
            typeBadge = `<span class="bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">🔴 EXPENSE</span>`;
            amtColor = "text-rose-400";
            amtPrefix = "-";
        }

        const reasonText = t.merchant || t.notes || t.category;
        const isSettled = (t.notes || "").includes("[PAID");

        let actionHtml = `
          <button onclick="deleteTx(${t.id})" class="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-slate-800 transition" title="Delete Entry">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        `;

        if (isUdhaar) {
            if (!isSettled) {
                actionHtml = `
                  <div class="flex items-center justify-center gap-1">
                    <button onclick="settleUdhaar(${t.id}, '${escapeHtml(t.merchant)}')" class="bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-2 py-1 rounded shadow flex items-center gap-1 transition" title="Customer Returned Money Today">
                      Receive
                    </button>
                    <button onclick="deleteTx(${t.id})" class="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-slate-800 transition" title="Delete">
                      <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                  </div>
                `;
            } else {
                actionHtml = `<span class="text-[10px] font-bold text-emerald-400 bg-emerald-500/20 px-2 py-0.5 rounded-full">✓ Paid</span>`;
            }
        }

        rowsHtml += `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="p-3.5">${typeBadge}</td>
            <td class="p-3.5">
              <div class="font-semibold text-slate-200">${escapeHtml(reasonText)}</div>
              <div class="text-[10px] text-slate-400">${escapeHtml(t.category)}</div>
            </td>
            <td class="p-3.5">
              <span class="text-slate-300">${t.payment_method}</span>
            </td>
            <td class="p-3.5 text-right font-bold ${amtColor}">
              ${amtPrefix}${formatMoney(t.total_amount)}
            </td>
            <td class="p-3.5 text-center">
              ${actionHtml}
            </td>
          </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
    if (window.lucide) lucide.createIcons();
}

// =============================================================================
// MANUAL ENTRY (EXPENSE / CASH IN / UDHAAR GIVEN / UDHAAR RETURNED)
// =============================================================================
function setEntryType(type) {
    activeEntryType = type;
    const btnExp = document.getElementById("btn-type-expense");
    const btnCrd = document.getElementById("btn-type-credit");
    const btnUdh = document.getElementById("btn-type-udhaar");
    const btnUdhRet = document.getElementById("btn-type-udhaar-ret");
    const descIn = document.getElementById("entryDesc");
    const catIn = document.getElementById("entryCategory");
    const custWrap = document.getElementById("entryCustomerSelectWrapper");
    const descLabel = document.getElementById("entryDescLabel");

    if (btnExp) btnExp.className = "py-2 text-xs font-bold rounded-lg transition text-slate-400 hover:text-white";
    if (btnCrd) btnCrd.className = "py-2 text-xs font-bold rounded-lg transition text-slate-400 hover:text-white";
    if (btnUdh) btnUdh.className = "py-2 text-xs font-bold rounded-lg transition text-slate-400 hover:text-white";
    if (btnUdhRet) btnUdhRet.className = "py-2 text-xs font-bold rounded-lg transition text-slate-400 hover:text-white";

    if (type === "Expense") {
        if (btnExp) btnExp.className = "py-2 text-xs font-bold rounded-lg transition bg-rose-600 text-white shadow";
        if (catIn) catIn.value = "Daily Expense";
        if (descIn) descIn.placeholder = "Reason / Description (e.g. Marker Salary, AC Diesel, Tea/Canteen)";
        if (custWrap) custWrap.classList.add("hidden");
        if (descLabel) descLabel.textContent = "Description / Reason *";
    } else if (type === "Credit") {
        if (btnCrd) btnCrd.className = "py-2 text-xs font-bold rounded-lg transition bg-emerald-600 text-white shadow";
        if (catIn) catIn.value = "Table Play";
        if (descIn) descIn.placeholder = "Description (e.g. Table Play Counter Sales, Canteen Collection)";
        if (custWrap) custWrap.classList.add("hidden");
        if (descLabel) descLabel.textContent = "Description / Counter Reason *";
    } else if (type === "Udhaar") {
        if (btnUdh) btnUdh.className = "py-2 text-xs font-bold rounded-lg transition bg-indigo-600 text-white shadow";
        if (catIn) catIn.value = "Other";
        if (descIn) descIn.placeholder = "👤 Customer / Member Name (e.g. Chatta, Hamza, Moez)";
        if (custWrap) custWrap.classList.remove("hidden");
        if (descLabel) descLabel.textContent = "Or Type Custom Customer Name *";
    } else if (type === "UdhaarReturned") {
        if (btnUdhRet) btnUdhRet.className = "py-2 text-xs font-bold rounded-lg transition bg-purple-600 text-white shadow";
        if (catIn) catIn.value = "Other";
        if (descIn) descIn.placeholder = "👤 Customer / Member Name (e.g. Chatta, Hamza, Moez)";
        if (custWrap) custWrap.classList.remove("hidden");
        if (descLabel) descLabel.textContent = "Or Type Custom Customer Name *";
    }
}

function onManualCustomerSelect(val) {
    const descIn = document.getElementById("entryDesc");
    if (!descIn) return;
    if (val === "__new__") {
        descIn.value = "";
        descIn.focus();
    } else if (val) {
        descIn.value = val;
    }
}

async function submitManualEntry(e) {
    e.preventDefault();
    const amt = parseFloat(document.getElementById("entryAmount").value);
    const cat = document.getElementById("entryCategory").value;
    const desc = document.getElementById("entryDesc").value.trim();

    if (!amt || amt <= 0) {
        alert("Please enter a valid positive amount.");
        return;
    }

    if ((activeEntryType === "Udhaar" || activeEntryType === "UdhaarReturned") && !desc) {
        alert("Please select or enter the Customer / Member Name.");
        return;
    }

    try {
        const res = await fetch("/api/entry", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                date: activeDate,
                amount: amt,
                tx_type: activeEntryType,
                category: cat,
                description: desc
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to save entry");
        }

        document.getElementById("entryAmount").value = "";
        document.getElementById("entryDesc").value = "";
        const entryMenu = document.getElementById("entryCustomerSelect");
        if (entryMenu) entryMenu.value = "";

        await refreshDayView();
    } catch (e) {
        alert(e.message);
    }
}

async function settleUdhaar(txId, custName) {
    const payMethod = confirm(`Member "${custName}" is paying back their Udhaar now.\n\nClick OK for CASH recovery, or Cancel for BANK recovery.`) ? "Cash" : "Bank";

    try {
        const res = await fetch("/api/settle-udhaar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tx_id: txId,
                settle_into: payMethod,
                settle_date: activeDate
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to settle transaction");
        }

        await refreshDayView();
        alert(`✅ Settled Udhaar of ${custName} into ${payMethod}!`);
    } catch (e) {
        alert(e.message);
    }
}

// =============================================================================
// SLIP & RECEIPT DRAG & DROP / CAMERA UPLOAD
// =============================================================================
function setupDropzone() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover"].forEach(event => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            dropzone.classList.add("border-brand-500", "bg-brand-500/10");
        });
    });

    ["dragleave", "drop"].forEach(event => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            dropzone.classList.remove("border-brand-500", "bg-brand-500/10");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleFileSelect(files);
        }
    });
}

function onCustomerSelectChanged(val) {
    const newWrapper = document.getElementById("uploadNewCustomerWrapper");
    if (!newWrapper) return;
    if (val === "__new__") {
        newWrapper.classList.remove("hidden");
        document.getElementById("uploadNewCustomerNameInput")?.focus();
    } else {
        newWrapper.classList.add("hidden");
    }
}

function populateUploadCustomerSelect() {
    let baseOptions = "";
    if (khataClientsList && khataClientsList.length > 0) {
        khataClientsList.forEach(c => {
            baseOptions += `<option value="${escapeHtml(c.customer_name)}">${escapeHtml(c.customer_name)} (PKR ${c.pending_balance.toLocaleString()} pending)</option>`;
        });
    }

    // 1. Slip uploader customer menu
    const uploadMenu = document.getElementById("uploadCustomerSelectMenu");
    if (uploadMenu) {
        uploadMenu.innerHTML = `<option value="">-- None (Bank Receipt) --</option>` + baseOptions + `<option value="__new__">➕ Enter New Customer...</option>`;
    }

    // 2. Manual Counter Entry customer menu
    const entryMenu = document.getElementById("entryCustomerSelect");
    if (entryMenu) {
        entryMenu.innerHTML = `<option value="">-- Select Customer from List (${khataClientsList.length} accounts) --</option>` + baseOptions + `<option value="__new__">➕ Enter New Customer...</option>`;
    }

    // 3. Direct Modal menu
    const directMenu = document.getElementById("directUdhaarCustomerSelect");
    if (directMenu) {
        directMenu.innerHTML = `<option value="">-- Select Customer --</option>` + baseOptions + `<option value="__new__">➕ Enter New Customer...</option>`;
    }

    // 4. Autocomplete Datalist
    const dl = document.getElementById("khataCustomerDatalist");
    if (dl && khataClientsList) {
        dl.innerHTML = khataClientsList.map(c => `<option value="${escapeHtml(c.customer_name)}">PKR ${c.pending_balance.toLocaleString()} pending</option>`).join("");
    }
}

function compressImageFile(file, maxWidth = 1280, quality = 0.82) {
    return new Promise((resolve) => {
        if (!file.type || !file.type.startsWith("image/") || file.type === "image/svg+xml") {
            return resolve(file);
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxWidth) {
                    if (width > height) {
                        height = Math.round((height * maxWidth) / width);
                        width = maxWidth;
                    } else {
                        width = Math.round((width * maxWidth) / height);
                        height = maxWidth;
                    }
                }

                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob(
                    (blob) => {
                        if (blob && blob.size < file.size) {
                            const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, ".jpg"), {
                                type: "image/jpeg",
                                lastModified: Date.now()
                            });
                            resolve(compressedFile);
                        } else {
                            resolve(file);
                        }
                    },
                    "image/jpeg",
                    quality
                );
            };
            img.onerror = () => resolve(file);
            img.src = e.target.result;
        };
        reader.onerror = () => resolve(file);
        reader.readAsDataURL(file);
    });
}

async function handleFileSelect(files) {
    if (!files || files.length === 0) return;

    // 1. Customer Udhaar Section
    const selVal = document.getElementById("uploadCustomerSelectMenu")?.value || "";
    let customerName = "";
    let slipType = "Bank Receipt";

    if (selVal === "__new__") {
        customerName = document.getElementById("uploadNewCustomerNameInput")?.value.trim() || "";
        if (!customerName) {
            alert("⚠️ Please enter the new customer's name, or select '-- None (Bank Receipt) --'.");
            document.getElementById("uploadNewCustomerNameInput")?.focus();
            return;
        }
        slipType = "Udhaar";
    } else if (selVal) {
        customerName = selVal;
        slipType = "Udhaar";
    }

    // 2. Extras Deducted Section
    const extrasDeducted = parseFloat(document.getElementById("uploadExtrasDeducted")?.value) || 0;
    const extrasReason = document.getElementById("uploadExtrasReason")?.value.trim() || "";
    const udhaarAmount = parseFloat(document.getElementById("uploadUdhaarAmount")?.value) || 0;

    const dateVal = activeDate || new Date().toISOString().split("T")[0];

    const statusBanner = document.getElementById("uploadStatus");
    if (statusBanner) statusBanner.classList.remove("hidden");

    const formData = new FormData();
    formData.append("target_date", dateVal);
    formData.append("slip_type", slipType);
    formData.append("customer_name", customerName);
    formData.append("udhaar_amount", String(udhaarAmount));
    formData.append("extras_deducted", String(extrasDeducted));
    formData.append("extras_reason", extrasReason);

    for (let i = 0; i < files.length; i++) {
        const rawFile = files[i];
        let processedFile = rawFile;
        try {
            processedFile = await compressImageFile(rawFile);
        } catch (_) {}
        const safeName = processedFile.name || `photo_${Date.now()}_${i}.jpg`;
        formData.append("files", processedFile, safeName);
    }

    try {
        const res = await fetch("/api/upload-slips", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            let errorText = `Server error (${res.status})`;
            try {
                const text = await res.text();
                try {
                    const err = JSON.parse(text);
                    if (Array.isArray(err.detail)) {
                        errorText = err.detail.map(d => d.msg || JSON.stringify(d)).join(", ");
                    } else if (typeof err.detail === "string") {
                        errorText = err.detail;
                    } else if (err.message) {
                        errorText = err.message;
                    } else {
                        errorText = text || errorText;
                    }
                } catch (_) {
                    errorText = text || errorText;
                }
            } catch (_) {}
            throw new Error(errorText);
        }

        // Reset extras & udhaar inputs on success
        const extAmt = document.getElementById("uploadExtrasDeducted");
        const extRsn = document.getElementById("uploadExtrasReason");
        const udhAmt = document.getElementById("uploadUdhaarAmount");
        if (extAmt) extAmt.value = "";
        if (extRsn) extRsn.value = "";
        if (udhAmt) udhAmt.value = "";

        await refreshDayView();
        if (slipType === "Udhaar") {
            alert(`✅ Added Udhaar slip to customer '${customerName}'!`);
        } else {
            alert("✅ Slip uploaded and processed successfully!");
        }
    } catch (e) {
        alert("Upload Notice: " + (e.message || String(e)));
    } finally {
        if (statusBanner) statusBanner.classList.add("hidden");
        try {
            const fIn = document.getElementById("slipFileInput");
            if (fIn) fIn.value = "";
        } catch (_) {}
        try {
            const cIn = document.getElementById("cameraInput");
            if (cIn) cIn.value = "";
        } catch (_) {}
    }
}

// =============================================================================
// DELETE TRANSACTION
// =============================================================================
async function deleteTx(id) {
    if (!confirm(`Are you sure you want to delete entry #${id}?`)) return;

    try {
        const res = await fetch(`/api/transaction/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete transaction");
        await refreshDayView();
    } catch (e) {
        alert(e.message);
    }
}

// =============================================================================
// MONTHLY CLOSING & STATEMENT
// =============================================================================
async function loadMonthlyClosing(monthStr) {
    const tbody = document.getElementById("monthlyRegisterTbody");
    const tfoot = document.getElementById("monthlyRegisterTfoot");
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-500">Loading monthly closing data...</td></tr>`;
    if (tfoot) tfoot.innerHTML = "";

    try {
        const url = monthStr ? `/api/monthly-closing?month=${encodeURIComponent(monthStr)}` : "/api/monthly-closing";
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load monthly summary");
        const data = await res.json();

        activeSelectedMonth = data.month || "";

        const sel = document.getElementById("monthlySelectMonth");
        if (sel && data.available_months && data.available_months.length > 0) {
            sel.innerHTML = data.available_months.map(m => {
                const optDate = new Date(m + "-01");
                const label = optDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
                return `<option value="${m}" ${m === activeSelectedMonth ? "selected" : ""}>${label}</option>`;
            }).join("");
        }

        setElemText("monthlySubtitle", `Statement for ${activeSelectedMonth} (${data.total_days_recorded} closing days)`);
        setElemText("monthlyDaysCount", `${data.total_days_recorded} days recorded`);

        // 6 Summary Metric Cards
        setElemText("monthly-cash-in", formatMoney(data.tot_cash_sales || 0));
        setElemText("monthly-bank-in", formatMoney(data.tot_bank_slips || 0));
        setElemText("monthly-udhaar-ret", formatMoney(data.tot_udhaar_returned || 0));
        setElemText("monthly-gross-rev", formatMoney(data.gross_revenue || 0));
        setElemText("monthly-expenses", formatMoney(data.tot_expense || 0));

        const netEl = document.getElementById("monthly-net-profit");
        const netAmt = data.net_profit || 0;
        if (netEl) {
            netEl.textContent = formatMoney(netAmt);
            netEl.className = `text-lg sm:text-xl font-extrabold tracking-tight ${netAmt >= 0 ? "text-brand-300" : "text-rose-400"}`;
        }

        // Day-by-Day Register Rows
        const days = data.days || [];
        if (!tbody) return;

        if (days.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-500">No records found for ${activeSelectedMonth}.</td></tr>`;
            return;
        }

        let rowsHtml = "";
        days.forEach(d => {
            rowsHtml += `
              <tr class="hover:bg-slate-800/40 transition">
                <td class="p-3.5 font-bold text-white">${d.date}</td>
                <td class="p-3.5 text-right font-medium text-emerald-400">${d.cash_sales ? formatMoney(d.cash_sales) : "-"}</td>
                <td class="p-3.5 text-right font-medium text-sky-400">${d.bank_slips ? formatMoney(d.bank_slips) : "-"}</td>
                <td class="p-3.5 text-right font-medium text-purple-400">${d.udhaar_returned ? formatMoney(d.udhaar_returned) : "-"}</td>
                <td class="p-3.5 text-right font-bold text-white">${formatMoney(d.total_in)}</td>
                <td class="p-3.5 text-right font-medium text-rose-400">${d.expense ? formatMoney(d.expense) : "-"}</td>
                <td class="p-3.5 text-right font-extrabold ${d.net_balance >= 0 ? "text-brand-300" : "text-rose-400"}">${d.net_balance >= 0 ? "+" : ""}${formatMoney(d.net_balance)}</td>
                <td class="p-3.5 text-center"><button onclick="viewDateFromHistory('${d.date}')" class="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg border border-slate-700 transition">View Day</button></td>
              </tr>
            `;
        });
        tbody.innerHTML = rowsHtml;

        // Footer Total Row
        if (tfoot) {
            tfoot.innerHTML = `
              <tr>
                <td class="p-3.5 text-white">MONTH TOTAL</td>
                <td class="p-3.5 text-right text-emerald-400">${formatMoney(data.tot_cash_sales)}</td>
                <td class="p-3.5 text-right text-sky-400">${formatMoney(data.tot_bank_slips)}</td>
                <td class="p-3.5 text-right text-purple-400">${formatMoney(data.tot_udhaar_returned)}</td>
                <td class="p-3.5 text-right text-white font-extrabold">${formatMoney(data.gross_revenue)}</td>
                <td class="p-3.5 text-right text-rose-400">${formatMoney(data.tot_expense)}</td>
                <td class="p-3.5 text-right font-black ${netAmt >= 0 ? "text-brand-300" : "text-rose-400"}">${formatMoney(netAmt)}</td>
                <td></td>
              </tr>
            `;
        }

        // Expense Categories Grid
        const catsGrid = document.getElementById("monthlyCategoriesGrid");
        const cats = data.expense_categories || [];
        if (catsGrid) {
            if (cats.length === 0) {
                catsGrid.innerHTML = `<div class="col-span-full text-slate-500 text-xs">No expenses recorded for this month.</div>`;
            } else {
                catsGrid.innerHTML = cats.map(c => {
                    return `
                      <div class="bg-slate-800/80 border border-slate-700/60 p-3 rounded-xl flex items-center justify-between">
                        <div><div class="text-xs font-semibold text-slate-200">${escapeHtml(c.category)}</div><div class="text-[10px] text-slate-400">${c.count} transactions</div></div>
                        <div class="text-xs font-bold text-rose-400">${formatMoney(c.total)}</div>
                      </div>
                    `;
                }).join("");
            }
        }

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function exportSelectedMonthCSV() {
    window.location.href = `/api/export-csv?month_year=${encodeURIComponent(activeSelectedMonth)}`;
}

// =============================================================================
// CUSTOMER KHATA / UDHAAR DIRECTORY
// =============================================================================
async function loadKhataSummary() {
    const tbody = document.getElementById("khataTbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-slate-500">Loading Khata directory...</td></tr>`;

    try {
        const res = await fetch("/api/khata");
        if (!res.ok) throw new Error("Failed to load Khata directory");
        const data = await res.json();

        setElemText("khata-total-clients", data.total_clients || 0);
        setElemText("khata-total-given", formatMoney(data.total_given || 0));
        setElemText("khata-total-returned", formatMoney(data.total_returned || 0));
        
        const outEl = document.getElementById("khata-total-outstanding");
        const outAmt = data.total_outstanding || 0;
        if (outEl) {
            outEl.textContent = formatMoney(outAmt);
            outEl.className = `text-2xl sm:text-3xl font-extrabold tracking-tight ${outAmt > 0 ? "text-amber-300" : "text-emerald-300"}`;
        }

        khataClientsList = data.clients || [];
        renderKhataTable(khataClientsList);
        populateUploadCustomerSelect();

        const dl = document.getElementById("khataCustomerDatalist");
        if (dl && data.clients) {
            dl.innerHTML = data.clients.map(c => `<option value="${escapeHtml(c.customer_name)}">PKR ${c.pending_balance.toLocaleString()} pending</option>`).join("");
        }
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function filterKhataClients() {
    const q = (document.getElementById("khataSearchInput")?.value || "").toLowerCase().trim();
    if (!q) {
        renderKhataTable(khataClientsList);
        return;
    }
    const filtered = khataClientsList.filter(c => c.customer_name.toLowerCase().includes(q));
    renderKhataTable(filtered);
}

function renderKhataTable(clients) {
    const tbody = document.getElementById("khataTbody");
    setElemText("khataSubtitle", `${clients.length} customer account(s)`);
    if (!tbody) return;

    if (!clients || clients.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" class="p-8 text-center text-slate-500">
              <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
              No customer credit records found. Click '+ Add Customer' to register a customer!
            </td>
          </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    let html = "";
    clients.forEach(c => {
        const isCleared = c.pending_balance <= 0;
        const statusBadge = isCleared
            ? `<span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">✓ Cleared</span>`
            : `<span class="bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">⏳ Due: ${formatMoney(c.pending_balance)}</span>`;

        const recBtn = !isCleared 
            ? `<button onclick="quickReceivePaymentForClient('${escapeHtml(c.customer_name)}', ${c.pending_balance})" class="bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded-lg text-[10px] font-bold transition shadow flex items-center gap-1">💵 Receive</button>`
            : "";

        html += `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="p-3.5">
              <div class="font-bold text-white text-sm">${escapeHtml(c.customer_name)}</div>
              <div class="text-[10px] text-slate-400">${c.notes ? escapeHtml(c.notes) : `Last activity: ${c.last_date} (${c.total_entries} txs)`}</div>
            </td>
            <td class="p-3.5 font-medium text-slate-300">${c.phone ? escapeHtml(c.phone) : '<span class="text-slate-600 text-[11px]">-</span>'}</td>
            <td class="p-3.5 text-right font-semibold text-indigo-300">${formatMoney(c.total_given)}</td>
            <td class="p-3.5 text-right font-semibold text-purple-300">${formatMoney(c.total_returned)}</td>
            <td class="p-3.5 text-right font-extrabold ${c.pending_balance > 0 ? "text-amber-400" : "text-emerald-400"}">${formatMoney(c.pending_balance)}</td>
            <td class="p-3.5 text-center">${statusBadge}</td>
            <td class="p-3.5 text-center">
              <div class="flex items-center justify-center gap-1">
                ${recBtn}
                <button onclick="openAddUdhaarDirectModal('${escapeHtml(c.customer_name)}')" title="Add Udhaar Entry" class="bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/30 px-2 py-1 rounded-lg text-[10px] font-bold transition flex items-center gap-0.5">+ Udhaar</button>
                <button onclick="openEditCustomerModal('${escapeHtml(c.customer_name)}', '${escapeHtml(c.phone || '')}', '${escapeHtml(c.notes || '')}')" title="Edit Customer Details" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-lg border border-slate-700 text-[10px] font-medium transition flex items-center gap-0.5"><i data-lucide="edit-3" class="w-3 h-3"></i> Edit</button>
                <button onclick="viewCustomerLedger('${escapeHtml(c.customer_name)}')" title="View Full Statement" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded-lg border border-slate-700 text-[10px] font-medium transition flex items-center gap-0.5"><i data-lucide="book-open" class="w-3 h-3"></i> Ledger</button>
              </div>
            </td>
          </tr>
        `;
    });

    tbody.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

// Add Customer Modal
function openAddCustomerModal() {
    const m = document.getElementById("addCustomerModal");
    if (m) m.classList.remove("hidden");
    const inp = document.getElementById("addCustName");
    if (inp) { inp.value = ""; inp.focus(); }
    const ph = document.getElementById("addCustPhone");
    if (ph) ph.value = "";
    const bal = document.getElementById("addCustBalance");
    if (bal) bal.value = "";
    const n = document.getElementById("addCustNotes");
    if (n) n.value = "";
}

function closeAddCustomerModal() {
    const m = document.getElementById("addCustomerModal");
    if (m) m.classList.add("hidden");
}

async function submitAddCustomer(e) {
    e.preventDefault();
    const name = document.getElementById("addCustName")?.value.trim();
    if (!name) return;
    const phone = document.getElementById("addCustPhone")?.value.trim() || "";
    const initialBalance = parseFloat(document.getElementById("addCustBalance")?.value) || 0;
    const notes = document.getElementById("addCustNotes")?.value.trim() || "";

    try {
        const res = await fetch("/api/khata/customers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                phone,
                initial_balance: initialBalance,
                notes,
                date: activeDate
            })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to add customer");
        }
        closeAddCustomerModal();
        await loadKhataSummary();
        alert(`✅ Customer '${name}' added to Khata successfully!`);
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// Edit Customer Modal
function openEditCustomerModal(custName, phone, notes) {
    const m = document.getElementById("editCustomerModal");
    if (m) m.classList.remove("hidden");
    const old = document.getElementById("editCustOldName");
    if (old) old.value = custName;
    const inp = document.getElementById("editCustName");
    if (inp) { inp.value = custName; inp.focus(); }
    const ph = document.getElementById("editCustPhone");
    if (ph) ph.value = phone || "";
    const n = document.getElementById("editCustNotes");
    if (n) n.value = notes || "";
}

function closeEditCustomerModal() {
    const m = document.getElementById("editCustomerModal");
    if (m) m.classList.add("hidden");
}

async function submitEditCustomer(e) {
    e.preventDefault();
    const oldName = document.getElementById("editCustOldName")?.value;
    const newName = document.getElementById("editCustName")?.value.trim();
    if (!newName) return;
    const phone = document.getElementById("editCustPhone")?.value.trim() || "";
    const notes = document.getElementById("editCustNotes")?.value.trim() || "";

    try {
        const res = await fetch(`/api/khata/customers/${encodeURIComponent(oldName)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                new_name: newName,
                phone,
                notes
            })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to update customer");
        }
        closeEditCustomerModal();
        await loadKhataSummary();
        alert(`✅ Customer '${newName}' updated successfully!`);
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function deleteCustomerProfile() {
    const oldName = document.getElementById("editCustOldName")?.value;
    if (!oldName) return;
    if (!confirm(`Are you sure you want to remove customer '${oldName}' from the Khata directory?`)) return;

    try {
        const res = await fetch(`/api/khata/customers/${encodeURIComponent(oldName)}`, {
            method: "DELETE"
        });
        if (!res.ok) throw new Error("Failed to delete customer");
        closeEditCustomerModal();
        await loadKhataSummary();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// Direct Udhaar Modal
function openAddUdhaarDirectModal(prefilledCustomer = "") {
    const m = document.getElementById("addKhataUdhaarModal");
    if (m) m.classList.remove("hidden");
    const nameInp = document.getElementById("directUdhaarCustName");
    if (nameInp) {
        nameInp.value = prefilledCustomer || "";
        if (!prefilledCustomer) nameInp.focus();
    }
    const dInp = document.getElementById("directUdhaarDate");
    if (dInp) dInp.value = activeDate;
    const amtInp = document.getElementById("directUdhaarAmount");
    if (amtInp) {
        amtInp.value = "";
        if (prefilledCustomer) amtInp.focus();
    }
    const nInp = document.getElementById("directUdhaarNotes");
    if (nInp) nInp.value = "";
}

function closeAddKhataUdhaarModal() {
    const m = document.getElementById("addKhataUdhaarModal");
    if (m) m.classList.add("hidden");
}

async function submitAddKhataUdhaar(e) {
    e.preventDefault();
    const custName = document.getElementById("directUdhaarCustName")?.value.trim();
    if (!custName) return;
    const date = document.getElementById("directUdhaarDate")?.value || activeDate;
    const amount = parseFloat(document.getElementById("directUdhaarAmount")?.value) || 0;
    if (amount <= 0) {
        alert("Please enter a valid positive Udhaar amount");
        return;
    }
    const notes = document.getElementById("directUdhaarNotes")?.value.trim() || "";

    try {
        const res = await fetch("/api/khata/add-udhaar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_name: custName,
                amount,
                date,
                notes
            })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to record Udhaar");
        }
        closeAddKhataUdhaarModal();
        await loadKhataSummary();
        alert(`✅ Added PKR ${amount.toLocaleString()} Udhaar for customer '${custName}'!`);
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function viewCustomerLedger(custName) {
    setElemText("modalCustomerName", `📖 ${custName}'s Ledger`);
    const tbody = document.getElementById("modalLedgerTbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-500">Loading ledger history...</td></tr>`;
    
    const modal = document.getElementById("customerLedgerModal");
    if (modal) modal.classList.remove("hidden");

    try {
        const res = await fetch(`/api/khata/${encodeURIComponent(custName)}`);
        if (!res.ok) throw new Error("Failed to load customer history");
        const history = await res.json();

        if (!tbody) return;
        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-500">No records found.</td></tr>`;
            return;
        }

        let html = "";
        let finalBal = 0;
        history.forEach(t => {
            const isGiven = t.tx_type === "Udhaar";
            finalBal = t.running_balance || 0;
            const badge = isGiven 
                ? `<span class="text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-1.5 py-0.5 rounded text-[10px] font-bold">🔵 Udhaar Given</span>`
                : `<span class="text-purple-400 bg-purple-500/10 border border-purple-500/30 px-1.5 py-0.5 rounded text-[10px] font-bold">🟣 Returned</span>`;

            html += `
              <tr class="hover:bg-slate-800/40 transition">
                <td class="p-2.5 font-medium text-slate-300">${t.date}</td>
                <td class="p-2.5">${badge}</td>
                <td class="p-2.5 text-slate-400">${escapeHtml(t.notes || t.category)}</td>
                <td class="p-2.5 text-right font-bold ${isGiven ? "text-indigo-300" : "text-purple-300"}">${isGiven ? "+" : "-"}${formatMoney(t.total_amount)}</td>
                <td class="p-2.5 text-right font-extrabold ${finalBal > 0 ? "text-amber-400" : "text-emerald-400"}">${formatMoney(finalBal)}</td>
              </tr>
            `;
        });

        tbody.innerHTML = html;
        setElemText("modalNetBalanceSummary", `Current Outstanding: ${formatMoney(finalBal)}`);
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function closeCustomerLedgerModal() {
    const modal = document.getElementById("customerLedgerModal");
    if (modal) modal.classList.add("hidden");
}

async function quickReceivePaymentForClient(custName, dueAmt) {
    const rawAmt = prompt(`Member: ${custName}\nTotal Due: ${formatMoney(dueAmt)}\n\nEnter payment amount received today:`, dueAmt);
    if (!rawAmt) return;
    const amt = parseFloat(rawAmt);
    if (!amt || amt <= 0) {
        alert("Please enter a valid positive amount.");
        return;
    }

    try {
        const res = await fetch("/api/entry", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                date: activeDate,
                amount: amt,
                tx_type: "UdhaarReturned",
                category: "Udhaar Recovery",
                description: custName
            })
        });

        if (!res.ok) throw new Error("Failed to record payment");
        alert(`✅ Successfully recorded payment of ${formatMoney(amt)} from ${custName}!`);
        await loadKhataSummary();
        await refreshDayView();
    } catch (e) {
        alert(e.message);
    }
}

// =============================================================================
// STAFF & SALARY MANAGEMENT
// =============================================================================
async function loadStaffSummary() {
    const tbody = document.getElementById("staffTbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-500">Loading staff directory...</td></tr>`;

    try {
        const res = await fetch("/api/staff");
        if (!res.ok) throw new Error("Failed to load staff data");
        const data = await res.json();

        setElemText("staff-total-count", data.total_staff || 0);
        setElemText("staff-total-earned-today", formatMoney(data.total_earned_to_date || 0));
        setElemText("staffEarnedDaysSub", `Accrued up to Day ${data.current_day || 26} of ${data.month}`);
        setElemText("staff-total-payroll", formatMoney(data.total_payroll || 0));
        setElemText("staff-total-security", formatMoney(data.total_security_held || 0));
        setElemText("staff-total-paid", formatMoney(data.total_paid_month || 0));
        setElemText("staff-total-remaining", formatMoney(data.total_remaining_due || 0));
        setElemText("staffSubtitle", `Pay Day: 10th of Every Month • Fresh accrued salary as of Day ${data.current_day || 26}`);

        staffMembersList = data.staff || [];
        renderStaffTable(staffMembersList);
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function renderStaffTable(staffList) {
    const tbody = document.getElementById("staffTbody");
    if (!tbody) return;

    if (!staffList || staffList.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" class="p-8 text-center text-slate-500">
              <i data-lucide="users" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
              No staff members added yet. Click "+ Add Staff Member" above to register markers and employees!
            </td>
          </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    let html = "";
    staffList.forEach(s => {
        const isResigned = s.status === "Resigned";
        const statusBadge = isResigned
            ? `<span class="bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">Left (${s.leave_date || "Resigned"})</span>`
            : (s.status === "Active"
                ? `<span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full text-[10px] font-bold">Active</span>`
                : `<span class="bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full text-[10px] font-bold">Inactive</span>`);

        let actionBtns = "";
        if (!isResigned) {
            actionBtns = `
                <button onclick="openPaySalaryModal(${s.id}, '${escapeHtml(s.name)}', ${s.balance_due || s.effective_salary})" class="bg-brand-600 hover:bg-brand-500 text-white px-2.5 py-1 rounded-lg text-[11px] font-bold transition shadow" title="Pay Salary or Advance">
                  💵 Pay
                </button>
                <button onclick="openResignModal(${s.id}, '${escapeHtml(s.name)}')" class="bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/30 px-2.5 py-1 rounded-lg text-[11px] font-bold transition" title="Mark Resigned / Left & Settle Security">
                  🚪 Left / Settle
                </button>
                <button onclick="viewStaffHistory('${escapeHtml(s.name)}')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-1 rounded-lg border border-slate-700 text-[11px] transition" title="View Payout History">
                  📖 History
                </button>
                <button onclick="deleteStaffMember(${s.id}, '${escapeHtml(s.name)}')" class="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-slate-800 transition" title="Delete Staff Member">
                  <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            `;
        } else {
            actionBtns = `
                <button onclick="reopenStaffMember(${s.id}, '${escapeHtml(s.name)}')" class="bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/30 px-2.5 py-1 rounded-lg text-[11px] font-bold transition" title="Reactivate Staff Member">
                  🔄 Rehire
                </button>
                <button onclick="viewStaffHistory('${escapeHtml(s.name)}')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-1 rounded-lg border border-slate-700 text-[11px] transition" title="View Payout History">
                  📖 History
                </button>
                <button onclick="deleteStaffMember(${s.id}, '${escapeHtml(s.name)}')" class="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-slate-800 transition" title="Delete">
                  <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            `;
        }

        html += `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="p-3.5">
              <div class="font-bold text-white text-sm">${escapeHtml(s.name)}</div>
              <div class="text-[10px] text-slate-400">${s.phone || "No phone"} ${s.hire_date ? "• Joined: " + s.hire_date : ""} ${s.leave_date ? "• Left: " + s.leave_date : ""}</div>
            </td>
            <td class="p-3.5 font-medium text-slate-300">
              <span class="bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-[11px] text-emerald-300 font-semibold">${escapeHtml(s.role)}</span>
              <span class="text-[10px] text-slate-500 block mt-0.5">${s.salary_type}</span>
            </td>
            <td class="p-3.5 text-right font-medium text-slate-400">${formatMoney(s.base_salary)}</td>
            <td class="p-3.5 text-right font-bold text-emerald-400">
              ⚡ ${formatMoney(s.earned_to_date)}
              <span class="text-[10px] text-emerald-400/80 font-semibold block">${s.days_worked_to_date} days worked</span>
            </td>
            <td class="p-3.5 text-right font-bold text-sky-400">
              ${formatMoney(s.effective_salary)}
              ${s.is_prorated ? `<span class="text-[10px] text-amber-400 font-semibold block">(${s.projected_days_worked}d month)</span>` : `<span class="text-[10px] text-slate-500 block">full month</span>`}
            </td>
            <td class="p-3.5 text-right font-semibold text-indigo-300">
              🔒 ${formatMoney(s.security_held)}
              <span class="text-[10px] ${s.security_days_held >= 10 ? 'text-emerald-400' : 'text-amber-400'} font-semibold block">
                ${s.security_days_held >= 10 ? '10/10d complete' : `${s.security_days_held}/10d withheld`}
              </span>
            </td>
            <td class="p-3.5 text-right font-bold text-purple-400">${formatMoney(s.paid_this_month)}</td>
            <td class="p-3.5 text-center">${statusBadge}</td>
            <td class="p-3.5 text-center">
              <div class="flex items-center justify-center gap-1.5">
                ${actionBtns}
              </div>
            </td>
          </tr>
        `;
    });

    tbody.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

function openAddStaffModal() {
    const modal = document.getElementById("addStaffModal");
    if (modal) modal.classList.remove("hidden");
}

function closeAddStaffModal() {
    const modal = document.getElementById("addStaffModal");
    if (modal) modal.classList.add("hidden");
}

async function submitAddStaff(e) {
    e.preventDefault();
    const name = document.getElementById("addStaffName")?.value.trim();
    const role = document.getElementById("addStaffRole")?.value;
    const salaryType = document.getElementById("addStaffSalaryType")?.value;
    const salary = parseFloat(document.getElementById("addStaffSalary")?.value) || 0;
    const hireDate = document.getElementById("addStaffHireDate")?.value || "";
    const phone = document.getElementById("addStaffPhone")?.value.trim();
    const notes = document.getElementById("addStaffNotes")?.value.trim();

    if (!name) {
        alert("Please enter staff name.");
        return;
    }

    try {
        const res = await fetch("/api/staff", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name, role, phone, salary_type: salaryType, base_salary: salary, hire_date: hireDate, notes
            })
        });

        if (!res.ok) throw new Error("Failed to add staff member");
        closeAddStaffModal();
        alert(`✅ Successfully registered staff member ${name}!`);
        await loadStaffSummary();
    } catch (e) {
        alert(e.message);
    }
}

function openPaySalaryModal(staffId, staffName, dueAmt) {
    document.getElementById("payModalStaffId").value = staffId;
    setElemText("payModalStaffName", `💵 Pay ${staffName}`);
    setElemText("payModalStaffSub", `Remaining Due: ${formatMoney(dueAmt)}`);
    document.getElementById("payModalAmount").value = dueAmt > 0 ? dueAmt : "";
    document.getElementById("payModalDate").value = activeDate;
    document.getElementById("payModalNotes").value = "";

    const modal = document.getElementById("paySalaryModal");
    if (modal) modal.classList.remove("hidden");
}

function closePaySalaryModal() {
    const modal = document.getElementById("paySalaryModal");
    if (modal) modal.classList.add("hidden");
}

async function submitPaySalary(e) {
    e.preventDefault();
    const staffId = parseInt(document.getElementById("payModalStaffId")?.value);
    const amount = parseFloat(document.getElementById("payModalAmount")?.value);
    const method = document.getElementById("payModalMethod")?.value;
    const payDate = document.getElementById("payModalDate")?.value || activeDate;
    const notes = document.getElementById("payModalNotes")?.value.trim();

    if (!amount || amount <= 0) {
        alert("Please enter a valid amount.");
        return;
    }

    try {
        const res = await fetch("/api/staff/pay", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                staff_id: staffId,
                amount,
                payment_method: method,
                pay_date: payDate,
                notes
            })
        });

        if (!res.ok) throw new Error("Failed to record salary payout");
        closePaySalaryModal();
        alert(`✅ Successfully recorded salary payment of ${formatMoney(amount)}!`);
        await loadStaffSummary();
        await refreshDayView();
    } catch (e) {
        alert(e.message);
    }
}

// =============================================================================
// RESIGNATION & FINAL SETTLEMENT HANDLERS
// =============================================================================
let currentSettlementCalculation = null;

async function openResignModal(staffId, staffName) {
    document.getElementById("resignStaffId").value = staffId;
    setElemText("resignModalStaffName", `🚪 Settle Resignation: ${staffName}`);
    document.getElementById("resignLeaveDate").value = activeDate;
    document.getElementById("resignDeductions").value = "0";
    document.getElementById("resignRefundSecurity").checked = true;
    document.getElementById("resignNotes").value = "";

    const modal = document.getElementById("resignationModal");
    if (modal) modal.classList.remove("hidden");

    await fetchSettlementCalculation();
}

function closeResignationModal() {
    const modal = document.getElementById("resignationModal");
    if (modal) modal.classList.add("hidden");
}

async function fetchSettlementCalculation() {
    const staffId = document.getElementById("resignStaffId")?.value;
    if (!staffId) return;

    const leaveDate = document.getElementById("resignLeaveDate")?.value || activeDate;
    const refundSec = document.getElementById("resignRefundSecurity")?.checked ? "true" : "false";
    const deductions = parseFloat(document.getElementById("resignDeductions")?.value) || 0;

    try {
        const url = `/api/staff/${staffId}/calculate-settlement?leave_date=${encodeURIComponent(leaveDate)}&refund_security=${refundSec}&deductions=${deductions}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Calculation error");
        const data = await res.json();
        currentSettlementCalculation = data;

        setElemText("resignSecHeldLabel", `+ ${formatMoney(data.security_deposit_held)}`);
        setElemText("calcDaysWorked", `${data.days_worked_in_final_month} day(s)`);
        setElemText("calcEarnedSalary", formatMoney(data.earned_salary));
        setElemText("calcSecurityRefund", `+ ${formatMoney(data.security_refund_amount)}`);
        setElemText("calcDeductions", `- ${formatMoney(data.deductions)}`);
        setElemText("calcNetPayable", formatMoney(data.net_settlement_payable));
    } catch (e) {
        console.error("Settlement calculation failed:", e);
    }
}

async function submitResignation(e) {
    e.preventDefault();
    const staffId = parseInt(document.getElementById("resignStaffId")?.value);
    const leaveDate = document.getElementById("resignLeaveDate")?.value || activeDate;
    const method = document.getElementById("resignPaymentMethod")?.value;
    const refundSec = document.getElementById("resignRefundSecurity")?.checked;
    const deductions = parseFloat(document.getElementById("resignDeductions")?.value) || 0;
    const notes = document.getElementById("resignNotes")?.value.trim();
    const netAmount = currentSettlementCalculation ? currentSettlementCalculation.net_settlement_payable : 0;

    if (!confirm(`Confirm final settlement and resignation for this staff member?\n\nTotal Settlement Payout: ${formatMoney(netAmount)}\nEffective Leave Date: ${leaveDate}`)) {
        return;
    }

    try {
        const res = await fetch(`/api/staff/${staffId}/settle-resignation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                leave_date: leaveDate,
                final_amount: netAmount,
                refund_security: refundSec,
                deductions: deductions,
                payment_method: method,
                notes: notes,
                pay_now: true
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to process resignation");
        }

        closeResignationModal();
        alert(`✅ Resignation & settlement successfully recorded! Final payout of ${formatMoney(netAmount)} logged as today's closing expense.`);
        await loadStaffSummary();
        await refreshDayView();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function reopenStaffMember(staffId, staffName) {
    if (!confirm(`Reactivate "${staffName}" back to Active staff?`)) return;

    try {
        const res = await fetch(`/api/staff/${staffId}/reopen`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to reactivate staff member");
        alert(`✅ "${staffName}" is now active again!`);
        await loadStaffSummary();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function viewStaffHistory(staffName) {
    setElemText("staffHistoryModalTitle", `📖 Payout History: ${staffName}`);
    const tbody = document.getElementById("staffHistoryModalTbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-500">Loading payout records...</td></tr>`;

    const modal = document.getElementById("staffHistoryModal");
    if (modal) modal.classList.remove("hidden");

    try {
        const res = await fetch(`/api/staff/${encodeURIComponent(staffName)}/history`);
        if (!res.ok) throw new Error("Failed to load staff history");
        const history = await res.json();

        if (!tbody) return;
        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-500">No salary or advance payouts recorded for this staff member yet.</td></tr>`;
            setElemText("staffHistoryModalTotal", "Total Paid: PKR 0.00");
            return;
        }

        let html = "";
        let totPaid = 0;
        history.forEach(t => {
            totPaid += t.total_amount || 0;
            html += `
              <tr class="hover:bg-slate-800/40 transition">
                <td class="p-2.5 font-medium text-slate-300">${t.date}</td>
                <td class="p-2.5 font-bold text-white">${escapeHtml(t.merchant)}</td>
                <td class="p-2.5 text-slate-400">${t.payment_method}</td>
                <td class="p-2.5 text-slate-400">${escapeHtml(t.notes || "-")}</td>
                <td class="p-2.5 text-right font-bold text-rose-400">-${formatMoney(t.total_amount)}</td>
              </tr>
            `;
        });

        tbody.innerHTML = html;
        setElemText("staffHistoryModalTotal", `Total Paid: ${formatMoney(totPaid)}`);
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function closeStaffHistoryModal() {
    const modal = document.getElementById("staffHistoryModal");
    if (modal) modal.classList.add("hidden");
}

async function deleteStaffMember(staffId, staffName) {
    if (!confirm(`Are you sure you want to remove staff member "${staffName}"?`)) return;

    try {
        const res = await fetch(`/api/staff/${staffId}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete staff member");
        await loadStaffSummary();
    } catch (e) {
        alert(e.message);
    }
}

// =============================================================================
// HISTORY & EXPORTS
// =============================================================================
async function loadHistory() {
    const tbody = document.getElementById("historyTbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-500">Loading closings history...</td></tr>`;

    try {
        const res = await fetch("/api/closings?sort_by=date_asc");
        if (!res.ok) throw new Error("Failed to load closings");
        const closings = await res.json();

        if (!tbody) return;
        if (closings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-500">No daily closings recorded yet.</td></tr>`;
            return;
        }

        let html = "";
        closings.forEach(c => {
            const cash = c.cash_credit || 0;
            const bank = c.bank_credit || (c.total_credit - cash);
            const exp = c.total_expense || 0;
            const totSales = c.total_credit || 0;
            const net = c.net_balance !== undefined ? c.net_balance : (totSales - exp);

            html += `
              <tr class="hover:bg-slate-800/40 transition">
                <td class="p-3.5 font-bold text-white">${c.date}</td>
                <td class="p-3.5 text-right text-emerald-400">${formatMoney(cash)}</td>
                <td class="p-3.5 text-right text-sky-400">${formatMoney(bank)}</td>
                <td class="p-3.5 text-right font-semibold text-white">${formatMoney(totSales)}</td>
                <td class="p-3.5 text-right text-rose-400">${formatMoney(exp)}</td>
                <td class="p-3.5 text-right font-extrabold ${net >= 0 ? "text-brand-400" : "text-rose-400"}">${formatMoney(net)}</td>
                <td class="p-3.5 text-center">
                  <button onclick="viewDateFromHistory('${c.date}')" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg border border-slate-700 transition">
                    View
                  </button>
                </td>
              </tr>
            `;
        });

        tbody.innerHTML = html;
    } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-rose-400">${e.message}</td></tr>`;
    }
}

function viewDateFromHistory(dateStr) {
    activeDate = dateStr;
    const dInput = document.getElementById("activeDateInput");
    if (dInput) dInput.value = dateStr;
    switchTab("daily");
    refreshDayView();
}

function downloadRionCSV() {
    window.location.href = "/api/export-csv";
}

// =============================================================================
// AI ASSISTANT CHAT
// =============================================================================
async function submitChat(e) {
    e.preventDefault();
    const input = document.getElementById("chatInput");
    const msg = input?.value.trim();
    if (!msg) return;

    const chatHist = document.getElementById("chatHistory");
    if (chatHist) {
        chatHist.innerHTML += `
          <div class="flex items-start space-x-3 justify-end">
            <div class="bg-purple-600 p-3 rounded-2xl rounded-tr-none text-white text-xs max-w-xl">
              ${escapeHtml(msg)}
            </div>
          </div>
        `;
        chatHist.scrollTop = chatHist.scrollHeight;
    }

    if (input) input.value = "";

    const loaderId = "loader-" + Date.now();
    if (chatHist) {
        chatHist.innerHTML += `
          <div id="${loaderId}" class="flex items-start space-x-3">
            <div class="w-8 h-8 rounded-full bg-purple-600/20 text-purple-400 flex items-center justify-center text-xs font-bold">AI</div>
            <div class="bg-slate-800 p-3.5 rounded-2xl rounded-tl-none border border-slate-700/60 text-slate-400 text-xs flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-purple-400 animate-bounce"></div>
              Analyzing Rion Snooker financials...
            </div>
          </div>
        `;
        chatHist.scrollTop = chatHist.scrollHeight;
    }

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();
        const loaderEl = document.getElementById(loaderId);
        if (loaderEl) loaderEl.remove();

        if (chatHist) {
            chatHist.innerHTML += `
              <div class="flex items-start space-x-3">
                <div class="w-8 h-8 rounded-full bg-purple-600/20 text-purple-400 flex items-center justify-center text-xs font-bold">AI</div>
                <div class="bg-slate-800 p-3.5 rounded-2xl rounded-tl-none border border-slate-700/60 max-w-xl text-slate-200 text-xs leading-relaxed whitespace-pre-wrap">
                  ${escapeHtml(data.reply)}
                </div>
              </div>
            `;
            chatHist.scrollTop = chatHist.scrollHeight;
        }
    } catch (e) {
        const loaderEl = document.getElementById(loaderId);
        if (loaderEl) loaderEl.remove();
        alert("Chat Error: " + e.message);
    }
}

// =============================================================================
// SETTINGS
// =============================================================================
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        if (!res.ok) return;
        const s = await res.json();
        currentCurrency = s.currency || "PKR ";
        document.querySelectorAll(".currency-label").forEach(el => el.textContent = currentCurrency);
        const currIn = document.getElementById("settingCurrency");
        if (currIn) currIn.value = currentCurrency;
    } catch (e) {
        console.error("Error loading settings:", e);
    }
}

async function saveSettings(e) {
    e.preventDefault();
    const curr = document.getElementById("settingCurrency")?.value.trim();
    const key = document.getElementById("settingApiKey")?.value.trim();

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                currency: curr || "PKR ",
                gemini_api_key: key || undefined
            })
        });

        if (res.ok) {
            alert("Settings saved successfully!");
            await loadSettings();
            await refreshDayView();
        }
    } catch (e) {
        alert("Error saving settings: " + e.message);
    }
}

async function uploadDatabaseBackup(input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    if (!confirm(`Are you sure you want to restore the database from '${file.name}'? This will replace the current database.`)) {
        input.value = "";
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/backup/upload-db", {
            method: "POST",
            body: formData
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to upload database backup");
        }
        alert("✅ Database restored successfully! Reloading data...");
        window.location.reload();
    } catch (err) {
        alert("Error restoring database: " + err.message);
    } finally {
        input.value = "";
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================
function setElemText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function formatMoney(amount) {
    const num = parseFloat(amount) || 0;
    return `${currentCurrency}${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
