// Background Script
console.log("Background script berjalan. Mengawasi tab...");

// Mendengarkan event ketika tab baru dibuat
browser.tabs.onCreated.addListener((tab) => {
    // Jika tab baru memiliki opener (dibuka oleh tab lain)
    if (tab.openerTabId) {
        // Ambil info dari tab yang membukanya (Tab B)
        browser.tabs.get(tab.openerTabId).then(openerTab => {
            
            // Periksa apakah tab pembukanya adalah halaman transitions_start.php (Tab B)
            if (openerTab.url && openerTab.url.includes("seo-fast.ru/site_transitions/transitions_start.php")) {
                console.log("Tab Tugas (Iklan) terdeteksi:", tab.id, "| Dibuka oleh Tab B:", openerTab.id);
                
                // Cari tahu berapa lama timernya dari URL hash di Tab B
                let timer = 15; // Waktu default 15 detik jika gagal diekstrak
                try {
                    const url = new URL(openerTab.url);
                    const hash = url.searchParams.get('hash');
                    if (hash) {
                        // Decode base64 hash
                        const decoded = atob(hash);
                        // Mencari format timer dari serialized array PHP (contoh: "timer";s:2:"15")
                        const match = decoded.match(/"timer";s:\d+:"(\d+)"/);
                        if (match && match[1]) {
                            timer = parseInt(match[1], 10);
                        }
                    }
                } catch (e) {
                    console.error("Gagal mengekstrak timer, menggunakan default 15 detik:", e);
                }

                // Beri jeda ekstra 2 detik agar aman
                const waitTime = timer + 2; 
                console.log(`Menunggu ${waitTime} detik sebelum menutup otomatis...`);
                
                setTimeout(() => {
                    // 1. Tutup Tab C (Target Web Iklan)
                    browser.tabs.remove(tab.id).then(() => {
                        console.log(`Tab C (ID: ${tab.id}) ditutup otomatis.`);
                        
                        // 2. Fokuskan kembali ke Tab B agar script di dalamnya ter-trigger
                        // Ketika Tab B di-fokuskan, ia akan otomatis menutup dirinya sendiri
                        browser.tabs.update(openerTab.id, { active: true }).then(() => {
                            console.log(`Kembali fokus ke Tab B (ID: ${openerTab.id}).`);
                        }).catch(e => console.log("Gagal fokus Tab B:", e));
                        
                    }).catch(e => console.log("Gagal menutup Tab C:", e));
                    
                }, waitTime * 1000); // Konversi ke milidetik
            }
        }).catch(e => {
            // Bisa diabaikan jika tab pembuka sudah tidak ada
        });
    }
});
