// --------------------------- NAVIGATION ---------------------------
document.getElementById("home-link").addEventListener("click", showHome);
document.getElementById("books-link").addEventListener("click", showBooks);
document.getElementById("my-books-link").addEventListener("click", showMyBooks);
document.getElementById("login-link").addEventListener("click", showLogin);
document.getElementById("admin-link").addEventListener("click", showAdmin);
document.getElementById("logout-link").addEventListener("click", logout);

function showHome() {
    hideAllSections();
    document.getElementById("home-section").style.display = "block";
}

function showBooks() {
    hideAllSections();
    document.getElementById("books-section").style.display = "block";
    fetchBooks();
}

function showMyBooks() {
    hideAllSections();
    document.getElementById("my-books-section").style.display = "block";
    fetchMyBooks();
}

function showLogin() {
    hideAllSections();
    document.getElementById("login-section").style.display = "block";
}

function showAdmin() {
    hideAllSections();
    document.getElementById("admin-section").style.display = "block";
    fetchPendingReturns();
    fetchAllBorrowedBooks();
}

function hideAllSections() {
    const sections = ["home-section", "books-section", "my-books-section", "login-section", "admin-section"];
    sections.forEach(id => document.getElementById(id).style.display = "none");
}

// --------------------------- LOGIN / REGISTER ---------------------------
document.getElementById("register-btn").addEventListener("click", () => {
    const username = document.getElementById("register-username").value;
    const password = document.getElementById("register-password").value;

    fetch("http://127.0.0.1:5000/api/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user_name: username, password: password})
    })
    .then(res => res.json())
    .then(data => alert(data.message || data.error))
    .catch(err => console.error(err));
});

document.getElementById("login-btn").addEventListener("click", () => {
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    fetch("http://127.0.0.1:5000/loginJWT", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
    })
    .then(res => res.json())
    .then(data => {
        if(data.token){
            localStorage.setItem("token", data.token);
            localStorage.setItem("username", username); // Kullanıcı adını kaydet

            alert("Giriş başarılı!");

            document.getElementById("login-link").style.display = "none";
            document.getElementById("logout-link").style.display = "inline";
            if(username === "admin") document.getElementById("admin-link").style.display = "inline";

            // Kullanıcı adını header'da göster
            let userSpan = document.getElementById("current-user");
            if(!userSpan){
                userSpan = document.createElement("span");
                userSpan.id = "current-user";
                userSpan.style.marginLeft = "15px";
                document.querySelector("header").appendChild(userSpan);
            }
            userSpan.textContent = `Hoşgeldin, ${username}`;
        
            showHome();

        } else {
            alert(data.message);
        }
    })
    .catch(err => console.error(err));
});

function logout() {
    // LocalStorage temizliği
    localStorage.removeItem("token");
    localStorage.removeItem("username");

    // Menüleri sıfırla
    document.getElementById("login-link").style.display = "inline";
    document.getElementById("logout-link").style.display = "none";
    document.getElementById("admin-link").style.display = "none";

    // Kullanıcı adını header’dan kaldır
    const userSpan = document.getElementById("current-user");
    if (userSpan) userSpan.remove();

    // Kitap listelerini temizle
    const myBookList = document.getElementById("my-book-list");
    if (myBookList) myBookList.innerHTML = "";

    const allBorrowedList = document.getElementById("all-borrowed-list");
    if (allBorrowedList) allBorrowedList.innerHTML = "";

    const userBorrowedList = document.getElementById("user-borrowed-list");
    if (userBorrowedList) userBorrowedList.innerHTML = "";

    const bookBorrowedList = document.getElementById("book-borrowed-list");
    if (bookBorrowedList) bookBorrowedList.innerHTML = "";

    // Login ve register inputlarını temizle
    document.getElementById("login-username").value = "";
    document.getElementById("login-password").value = "";
    document.getElementById("register-username").value = "";
    document.getElementById("register-password").value = "";

    showHome();
}



// --------------------------- BOOKS ---------------------------
document.getElementById("search-btn").addEventListener("click", () => {
    const query = document.getElementById("search-query").value;
    searchBooks(query);
});

function fetchBooks() {
    fetch("http://127.0.0.1:5000/api/books")
        .then(res => res.json())
        .then(data => renderBookList(data))
        .catch(err => console.error(err));
}

function searchBooks(query) {
    if(!query) return fetchBooks();
    fetch(`http://127.0.0.1:5000/api/books/search?query=${query}`)
        .then(res => res.json())
        .then(data => renderBookList(data.results))
        .catch(err => console.error(err));
}

function renderBookList(data) {
    const bookList = document.getElementById("book-list");
    bookList.innerHTML = "";
    const token = localStorage.getItem("token");
    const currentUser = localStorage.getItem("username"); // Login sırasında bunu set etmeliyiz

    data.forEach(book => {
        const li = document.createElement("li");
        li.textContent = `${book.book_name} - ${book.writer} ${book.isAvailable === 0 ? "(Mevcut)" : "(Kiralanmış)"}`;

        // Sadece normal kullanıcılar kiralayabilir
        if(book.isAvailable === 0 && token && currentUser !== "admin"){
            const borrowBtn = document.createElement("button");
            borrowBtn.textContent = "Kirala";
            borrowBtn.addEventListener("click", () => borrowBook(book.id));
            li.appendChild(borrowBtn);
        }
        bookList.appendChild(li);
    });
}


function borrowBook(bookId) {
    const token = localStorage.getItem("token");
    if(!token) return alert("Önce giriş yapmalısınız!");

    fetch("http://127.0.0.1:5000/api/borrow", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({book_id: parseInt(bookId)})
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
        fetchBooks();
        fetchMyBooks();
    })
    .catch(err => console.error(err));
}

// --------------------------- MY BOOKS ---------------------------
function fetchMyBooks() {
    const token = localStorage.getItem("token");
    const username = localStorage.getItem("username");

    // Token yoksa veya admin kullanıcıysa engelle
    if (!token || !username || username === "admin") {
        alert("Önce normal kullanıcı olarak giriş yapmalısınız!");
        const myBookList = document.getElementById("my-book-list");
        if (myBookList) myBookList.innerHTML = ""; // Listeyi temizle
        return;
    }

    fetch("http://127.0.0.1:5000/api/my-books", {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => {
        const myBookList = document.getElementById("my-book-list");
        myBookList.innerHTML = "";

        if (!data.borrowed_books || data.borrowed_books.length === 0) {
            myBookList.innerHTML = "<li>Henüz ödünç alınan kitap yok.</li>";
            return;
        }

        data.borrowed_books.forEach(book => {
            const li = document.createElement("li");
            li.textContent = `${book.book_name} - ${book.author} | Ödünç: ${book.borrow_date} | İade: ${book.return_date || "Henüz iade edilmedi"}`;
            
            // İade edilmemişse buton ekle
            if (!book.return_date) { 
                const returnBtn = document.createElement("button");
                returnBtn.textContent = "İade Et";
                returnBtn.addEventListener("click", () => returnBook(book.book_id));
                li.appendChild(returnBtn);
            }

            myBookList.appendChild(li);
        });
    })
    .catch(err => console.error("Kitaplar alınırken hata:", err));
}


function returnBook(bookId) {
    const token = localStorage.getItem("token");
    fetch("http://127.0.0.1:5000/api/return", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({book_id: parseInt(bookId)})
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || data.error);
        fetchMyBooks(); 
        fetchBooks();   
    })
    .catch(err => console.error(err));
}

// --------------------------- ADMIN ---------------------------


// --------------------------- ADMIN: Pending Returns ---------------------------
const STATUS_OPTIONS = [
    { value: 2, label: "RETURNED_OK" },
    { value: 3, label: "DAMAGED" },
    { value: 4, label: "LATE" },
    { value: 5, label: "LOST" }
];

const STATUS_LABELS = {
    0: "PENDING",
    1: "NOT_RETURNED",
    2: "RETURNED_OK",
    3: "DAMAGED",
    4: "LATE",
    5: "LOST"
};

function fetchPendingReturns() {
    const token = localStorage.getItem("token");
    fetch("http://127.0.0.1:5000/api/admin/pending-returns", {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(res => res.json())
    .then(data => {
        const pendingList = document.getElementById("pending-returns-list");
        pendingList.innerHTML = "";

        if (!data.pending_returns || data.pending_returns.length === 0) {
            pendingList.innerHTML = "<li>Bekleyen iade yok.</li>";
            return;
        }

        data.pending_returns.forEach(item => {
            const li = document.createElement("li");

            const statusLabel = STATUS_LABELS[item.status] || (`UNKNOWN(${item.status})`);
            li.innerHTML = `<strong>${item.book_name}</strong> — ${item.user_name} | İade Tarihi: ${item.return_date || "—"} | Mevcut Durum: ${statusLabel}`;

            // select oluştur
            const select = document.createElement("select");
            const placeholderOpt = document.createElement("option");
            placeholderOpt.value = "";
            placeholderOpt.textContent = "--Durum seç--";
            select.appendChild(placeholderOpt);

            STATUS_OPTIONS.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.value;         // backend'e gidecek integer (string formunda, parse edilecek)
                opt.textContent = s.label;   // kullanıcıya görünen etiket
                select.appendChild(opt);
            });

            // Güncelle butonu
            const updateBtn = document.createElement("button");
            updateBtn.textContent = "Durumu Güncelle";
            updateBtn.addEventListener("click", () => {
                const val = select.value;
                if (!val) {
                    alert("Lütfen önce bir durum seçin.");
                    return;
                }
                updateReturnStatus(item.borrow_id, val);
            });

            li.appendChild(select);
            li.appendChild(updateBtn);
            pendingList.appendChild(li);
        });
    })
    .catch(err => {
        console.error("Pending returns alınırken hata:", err);
    });
}

function updateReturnStatus(borrowId, status) {
    const token = localStorage.getItem("token");
    fetch(`http://127.0.0.1:5000/api/admin/return-status/${borrowId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ status: parseInt(status) }) // **integer** gönderiyoruz
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message || "Durum güncellendi.");
            fetchPendingReturns(); // listeyi yenile
        }
    })
    .catch(err => {
        console.error("Durum güncellenirken hata:", err);
        alert("Durum güncellenirken hata oluştu.");
    });
}


// --------------------------- ALL BORROWED BOOKS ---------------------------
let currentPage = 1;
let totalPages = 1; // backend’den gelen toplam sayfa sayısı

function fetchAllBorrowedBooks() {
    const token = localStorage.getItem("token");
    fetch(`http://127.0.0.1:5000/api/admin/borrowed-books/page?page=${currentPage}`, {
        headers: {"Authorization": `Bearer ${token}`}
    })
    .then(res => res.json())
    .then(data => {
        const allList = document.getElementById("all-borrowed-list");
        allList.innerHTML = "";

        data.borrowed_books.forEach(item => {
            const li = document.createElement("li");
            li.textContent = `${item.user_name} -> ${item.book_name} | Ödünç: ${item.borrow_date} | İade: ${item.return_date || "Henüz iade edilmedi"}`;
            allList.appendChild(li);
        });

        totalPages = data.total_pages;

        const pageInfo = document.createElement("p");
        pageInfo.textContent = `Sayfa ${data.page} / ${data.total_pages}`;
        allList.appendChild(pageInfo);
    })
    .catch(err => console.error(err));
}

// İleri/geri tuşları
document.getElementById("prev-page-btn").addEventListener("click", () => {
    if(currentPage > 1){
        currentPage--;
        fetchAllBorrowedBooks();
    }
});

document.getElementById("next-page-btn").addEventListener("click", () => {
    if(currentPage < totalPages){
        currentPage++;
        fetchAllBorrowedBooks();
    }
});


// --------------------------- SINGLE USER BORROWED BOOKS ---------------------------
document.getElementById("user-books-btn").addEventListener("click", () => {
    const userId = parseInt(document.getElementById("user-id-input").value);
    if(!userId) return alert("User ID gerekli!");
    fetchUserBorrowedBooks(userId);
});

function fetchUserBorrowedBooks(userId){
    const token = localStorage.getItem("token");
    fetch(`http://127.0.0.1:5000/api/admin/borrowed-books-user/${userId}?page=1`, {
        headers: {"Authorization": `Bearer ${token}`}
    })
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById("user-borrowed-list");
        list.innerHTML = "";
        if(data.borrowed_books.length === 0){
            list.innerHTML = "<li>Bu kullanıcıya ait ödünç kitap yok.</li>";
            return;
        }
        data.borrowed_books.forEach(item => {
            const li = document.createElement("li");
            li.textContent = `${item.book_name} - ${item.author} | Ödünç: ${item.borrow_date} | İade: ${item.return_date || "Henüz iade edilmedi"}`;
            list.appendChild(li);
        });
    })
    .catch(err => console.error(err));
}

// --------------------------- SINGLE BOOK BORROWED RECORDS ---------------------------
document.getElementById("book-borrowed-btn").addEventListener("click", () => {
    const bookId = parseInt(document.getElementById("book-id-input").value);
    if(!bookId) return alert("Book ID gerekli!");
    fetchBookBorrowedRecords(bookId);
});

function fetchBookBorrowedRecords(bookId){
    const token = localStorage.getItem("token");
    fetch(`http://127.0.0.1:5000/api/admin/borrowed-books/${bookId}?page=1`, {
        headers: {"Authorization": `Bearer ${token}`}
    })
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById("book-borrowed-list");
        list.innerHTML = "";
        if(!data.borrowed_books || data.borrowed_books.length === 0){
            list.innerHTML = "<li>Bu kitap ile ilgili ödünç kaydı yok.</li>";
            return;
        }
        data.borrowed_books.forEach(item => {
            const li = document.createElement("li");
            li.textContent = `${item.kullanici_adi} -> ${item.book_name} | Ödünç: ${item.kiralama_tarihi} | İade: ${item.iade_tarihi || "Henüz iade edilmedi"}`;
            list.appendChild(li);
        });
    })
    .catch(err => console.error(err));
}


window.onload = () => {
    const token = localStorage.getItem("token");
    const username = localStorage.getItem("username");

    if (token && username) {
        // Kullanıcı giriş yapmış gibi menüleri ayarla
        document.getElementById("login-link").style.display = "none";
        document.getElementById("logout-link").style.display = "inline";

        if (username === "admin") {
            document.getElementById("admin-link").style.display = "inline";
        } else {
            document.getElementById("admin-link").style.display = "none";
        }

        // Header’da kullanıcı adı göster
        let userSpan = document.getElementById("current-user");
        if (!userSpan) {
            userSpan = document.createElement("span");
            userSpan.id = "current-user";
            userSpan.style.marginLeft = "15px";
            document.querySelector("header").appendChild(userSpan);
        }
        userSpan.textContent = `Hoşgeldin, ${username}`;
    } else {
        // Token yoksa giriş yapılmamış say
        logout();
    }
};
