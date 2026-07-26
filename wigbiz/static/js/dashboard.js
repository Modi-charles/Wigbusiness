const button =
document.getElementById("sidebarToggle");


const sidebar =
document.getElementById("sidebar");



button.onclick = function(){


if(window.innerWidth <= 768){

    sidebar.classList.toggle("show");

}

else{

    sidebar.classList.toggle("collapsed");

}


};