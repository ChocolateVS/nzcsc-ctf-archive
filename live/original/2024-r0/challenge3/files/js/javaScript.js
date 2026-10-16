function hide_all() {
    $("#tabs-home").css("display", "none");
    $("#tabs-comp").css("display", "none");
    $("#tabs-logistics").css("display", "none");
    $("#tabs-info").css("display", "none");
    $("#tabs-aboutus").css("display", "none");		
    $("#tabs-history").css("display", "none");				
}

function selected_page(pagename) {
    switch(pagename) {
    case "tabs-home":
      $(".navbar-nav .home").addClass("active");
      break;
    case "tabs-comp":
      $(".navbar-nav .competition").addClass("active");
      break;
    case "tabs-logistics":
      $(".navbar-nav .logistics").addClass("active");
      break;
    case "tabs-info":
        $(".navbar-nav .info").addClass("active");
    break;
    case "tabs-aboutus":
      $(".navbar-nav .aboutus").addClass("active");
      break;
    case "tabs-history":
      $(".navbar-nav .history").addClass("active");
      break;
    default:
      $(".navbar-nav .home").addClass("active");
      break;
  }   	
}

function goto_page(page_title, tab_index){
    hide_all();
	var displayed_tab = document.getElementById(page_title);
		
	$(displayed_tab).css("display", "flex").hide().fadeIn('slow');

    // Update the active menu item (the orange line)
    $(".navbar-nav .active").removeClass("active");
    selected_page(page_title);

    // don't fetch inner_html/home.html
		if(displayed_tab == "tabs-home")
        return;
}
