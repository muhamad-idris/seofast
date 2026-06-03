// ==UserScript==
// @name         SeoFast Auto Clicker (Userscript)
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Otomatisasi tugas klik pada situs SeoFast (versi Userscript untuk Tampermonkey/Violentmonkey)
// @author       tamsis xd
// @match        *://seo-fast.ru/work_transitions*
// @match        *://seo-fast.ru/site_transitions/transitions_start.php*
// @grant        unsafeWindow
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    const currentUrl = window.location.href;

    // ========================================================================
    // 1. LOGIKA UNTUK HALAMAN UTAMA (DAFTAR TUGAS)
    // ========================================================================
    if (currentUrl.includes("seo-fast.ru/work_transitions")) {
        console.log("SEO-Fast Userscript: Berada di halaman work_transitions, menyiapkan auto-clicker...");

        function startAutoClicker() {
            const taskElements = Array.from(document.querySelectorAll("a.surf_ckick[onclick^='start_transitions']"));
            
            const uniqueTasks = [];
            const seenIds = new Set();
            
            taskElements.forEach(task => {
                const match = task.getAttribute("onclick").match(/start_transitions\('(\d+)'\)/);
                if (match && match[1]) {
                    const taskId = match[1];
                    if (!seenIds.has(taskId)) {
                        seenIds.add(taskId);
                        uniqueTasks.push({ element: task, id: taskId });
                    }
                }
            });

            console.log(`SEO-Fast Userscript: Ditemukan ${uniqueTasks.length} tugas unik.`);

            if (uniqueTasks.length > 0) {
                let currentIndex = 0;

                function clickNextTask() {
                    if (currentIndex < uniqueTasks.length) {
                        const currentTask = uniqueTasks[currentIndex];
                        console.log(`SEO-Fast Userscript: Mengklik tugas ke-${currentIndex + 1} (ID: ${currentTask.id})`);
                        
                        currentTask.element.click();
                        currentIndex++;
                        
                        waitForTaskCompletion(currentTask.id);
                    } else {
                        console.log("SEO-Fast Userscript: Semua tugas di halaman ini telah diklik.");
                    }
                }

                function waitForTaskCompletion(taskId) {
                    let waited = 0;
                    const maxWait = 90; // Maksimal tunggu 90 detik per tugas
                    
                    const interval = setInterval(() => {
                        const container = document.getElementById(`res_views${taskId}`);
                        waited += 2;
                        
                        if (container) {
                            const text = container.innerText;
                            if (text.includes("Оплата") || text.includes("получена")) {
                                console.log(`SEO-Fast Userscript: Tugas ${taskId} SUKSES! Lanjut ke tugas berikutnya...`);
                                clearInterval(interval);
                                setTimeout(clickNextTask, 2000); 
                                return;
                            }
                        }
                        
                        if (waited >= maxWait) {
                            console.log(`SEO-Fast Userscript: Timeout! Melewati tugas ${taskId}...`);
                            clearInterval(interval);
                            setTimeout(clickNextTask, 1000);
                        }
                    }, 2000);
                }

                setTimeout(clickNextTask, 2000); 
            } else {
                console.log("SEO-Fast Userscript: Tidak ada tugas yang ditemukan.");
            }
        }

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", startAutoClicker);
        } else {
            startAutoClicker();
        }
    }

    // ========================================================================
    // 2. LOGIKA UNTUK TAB KEDUA (TIMER / TRANSITIONS START)
    // ========================================================================
    else if (currentUrl.includes("seo-fast.ru/site_transitions/transitions_start.php")) {
        console.log("SEO-Fast Userscript: Tab timer (Tab B) terdeteksi.");
        
        let timer = 15;
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const hash = urlParams.get('hash');
            if (hash) {
                const decoded = atob(hash);
                const match = decoded.match(/"timer";s:\d+:"(\d+)"/);
                if (match && match[1]) {
                    timer = parseInt(match[1], 10);
                }
            }
        } catch (e) {
            console.error("Gagal mengekstrak timer:", e);
        }

        const waitTime = timer + 2;
        console.log(`SEO-Fast Userscript: Akan memicu validasi selesai dalam ${waitTime} detik...`);

        // Mencegat (intercept) perintah buka tab iklan (Tab C) untuk mendapatkan referensinya
        if (typeof unsafeWindow !== 'undefined') {
            const originalOpen = unsafeWindow.open;
            unsafeWindow.open = function(url, windowName, windowFeatures) {
                console.log("SEO-Fast Userscript: Tab C dibuka oleh sistem:", url);
                const adWindow = originalOpen.call(unsafeWindow, url, windowName, windowFeatures);
                
                setTimeout(() => {
                    // Menutup Tab C secara paksa
                    try {
                        if (adWindow) {
                            adWindow.close();
                            console.log("SEO-Fast Userscript: Tab C berhasil ditutup otomatis.");
                        }
                    } catch(err) {
                        console.log("SEO-Fast Userscript: Gagal menutup Tab C (batas keamanan browser).");
                    }
                    
                    // Memanipulasi Tab B agar mengira user sudah kembali (focus)
                    unsafeWindow.dispatchEvent(new Event('focus'));
                    unsafeWindow.dispatchEvent(new Event('visibilitychange'));
                }, waitTime * 1000);
                
                return adWindow;
            };
        }

        // Backup plan: jika tab C tidak dibuka via window.open, kita tetap jalankan trigger validasi
        setTimeout(() => {
            console.log("SEO-Fast Userscript: Memicu event focus (fallback)...");
            window.dispatchEvent(new Event('focus'));
            document.dispatchEvent(new Event('visibilitychange'));
        }, waitTime * 1000);
    }

})();
