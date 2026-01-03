window.onload = function() {
    convertToSvanne();
};

function get_svanne(user_date) {
    const alphabet = {0:"A", 1:"B", 2:"C", 3:"D", 4:"E", 5:"F", 6:"G", 7:"H", 
                      8:"I", 9:"J", 10:"K", 11:"L", 12:"M", 13:"N", 14:"O", 
                      15:"P", 16:"Q", 17:"R", 18:"S", 19:"T", 20:"U", 21:"V", 
                      22:"W", 23:"X", 24:"Y", 25:"Z", 26:"+"};
    
    const year = user_date.getFullYear();
    
    const day_of_year = Math.floor((user_date - new Date(year, 0, 0)) / (1000 * 60 * 60 * 24));
    const al_key = Math.floor(day_of_year / 14);
    
    const svanne = `${(year-2022).toString().padStart(2, '0')}${alphabet[al_key]}${(day_of_year % 14).toString().padStart(2, '0')}`;
    return svanne
}

function convertToSvanne() {
    // If user_date is empty, use today's date
    const today = new Date();

    const result = get_svanne(today);
    document.getElementById("result").textContent = "Today's Date: " + result;
}