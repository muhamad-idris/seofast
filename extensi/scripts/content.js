// Berjalan di dalam konteks halaman web.
console.log("Content script dimuat di halaman:", window.location.href);

if (window.location.href.includes("seo-fast.ru/work_transitions")) {
    console.log("SEO-Fast Extensi: Berada di halaman work_transitions, menyiapkan auto-clicker...");

    function startAutoClicker() {
        // Cari semua elemen link tugas
        const taskElements = Array.from(document.querySelectorAll("a.surf_ckick[onclick^='start_transitions']"));
        
        // Satu tugas di tabel biasanya memiliki 2 elemen <a> dengan fungsi onclick yang sama.
        // Kita saring agar hanya menyimpan 1 objek tugas per ID.
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

        console.log(`SEO-Fast Extensi: Ditemukan ${uniqueTasks.length} tugas unik.`);

        if (uniqueTasks.length > 0) {
            let currentIndex = 0;

            function clickNextTask() {
                if (currentIndex < uniqueTasks.length) {
                    const currentTask = uniqueTasks[currentIndex];
                    console.log(`SEO-Fast Extensi: Mengklik tugas ke-${currentIndex + 1} (ID: ${currentTask.id})`);
                    
                    // Simulasikan klik pada tugas tersebut
                    currentTask.element.click();
                    
                    currentIndex++;
                    
                    // Alih-alih menunggu dengan waktu tetap, kita pantau perubahannya
                    waitForTaskCompletion(currentTask.id);
                } else {
                    console.log("SEO-Fast Extensi: Semua tugas di halaman ini telah diklik.");
                }
            }

            function waitForTaskCompletion(taskId) {
                let waited = 0;
                const maxWait = 90; // Maksimal menunggu 90 detik per tugas (antisipasi error/nyangkut)
                
                const interval = setInterval(() => {
                    // Cari container berdasarkan ID tugas
                    const container = document.getElementById(`res_views${taskId}`);
                    waited += 2;
                    
                    if (container) {
                        const text = container.innerText;
                        // Mengecek apakah terdapat teks "Оплата" (Bayaran) atau "получена" (Diterima)
                        // Teks lengkap dari gambar Anda: "Оплата получена +0.037 р."
                        if (text.includes("Оплата") || text.includes("получена")) {
                            console.log(`SEO-Fast Extensi: Tugas ${taskId} SUKSES! Bayaran diterima. Lanjut ke tugas berikutnya...`);
                            clearInterval(interval);
                            
                            // Beri jeda 2 detik sebelum ngeklik tugas berikutnya agar tidak dicurigai sistem
                            setTimeout(clickNextTask, 2000); 
                            return;
                        }
                    }
                    
                    // Jika waktu tunggu melebihi maxWait, lewati saja tugas ini agar tidak stuck
                    if (waited >= maxWait) {
                        console.log(`SEO-Fast Extensi: Timeout! Tugas ${taskId} tidak merespon setelah ${maxWait} detik. Melewati...`);
                        clearInterval(interval);
                        setTimeout(clickNextTask, 1000);
                    }
                }, 2000); // Cek secara berulang setiap 2 detik
            }

            // Mulai klik tugas pertama dengan jeda 2 detik setelah halaman dimuat
            setTimeout(clickNextTask, 2000); 
        } else {
            console.log("SEO-Fast Extensi: Tidak ada tugas yang ditemukan.");
        }
    }

    // Jalankan fungsi saat halaman dan DOM selesai dimuat
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startAutoClicker);
    } else {
        startAutoClicker();
    }
}

// Mendengarkan pesan dari background script atau popup (jika nanti diperlukan)
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("Pesan diterima di content script:", message);
});
