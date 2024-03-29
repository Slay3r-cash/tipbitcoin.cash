
// Global vars
var isPaid = 0;

// When the document is ready
$(document).ready(function() {
    // Events :)
    $('#user_form').submit(function (event) {
        createPayRequest();
    });
    $('#tip-again').hide();
    $('#back-btn').hide();
    $('#showModalButton').click(function (event) {
        $(this).prop('disabled',true).html('<div class="pull-left">Generating Address...</div>').append('<div class="loader-6 pull-left"><span></span></div>');
        $('#user_display').prop('disabled',true)
        $('#user_identifier').prop('disabled',true)
        $('#user_message').prop('disabled',true)
        $('#showSLPButton').prop('disabled',true)
        // Stop redirections
        event.preventDefault();
        // Call our create pay request function
        createPayRequest(
                $('#user_display').val(),
                $('#user_identifier').val(),
                $('#user_message').val(),
                socialId,
        );


    });
    $('#showSLPButton').click(function (event) {
        $(this).prop('disabled',true).html('<div class="pull-left">Generating Address...</div>').append('<div class="loader-6 pull-left"><span></span></div>');
        $('#user_display').prop('disabled',true)
        $('#user_identifier').prop('disabled',true)
        $('#user_message').prop('disabled',true)
	$('#showModalButton').prop('disabled',true)
        // Stop redirections
        event.preventDefault();
        // Call our create pay request function
        createPayRequestSLP(
                $('#user_display').val(),
                $('#user_identifier').val(),
                $('#user_message').val(),
                socialId,
        );


    });
    $('#testAlertButton').click(function (event) {
        // Stop redirections
        event.preventDefault();
        // Call our create pay request function
        sendTestAlert(
                socialId,
        );


    });

    $('#testAlertSLPButton').click(function (event) {
        // Stop redirections
        event.preventDefault();
        // Call our create pay request function
        sendTestAlertSLP(
                socialId,
        );


    });

});

// We'll keep it inline for now...
function createPayRequest(userDisplay, userIdentifier, userMessage, socialId){
    // Get the value of some things on our form
    //$('#myModal').modal('show');
    // Create a new request to our server
    console.log("Social ID: " + socialId);
    console.log("User ID: " + userIdentifier);
    console.log("User Msg: " + userMessage);
    console.log("User Name: " + userDisplay);



    var resp = $.post('/_create_payreq',
            // This will be formatted as a 'body' string in the post request
            {
                social_id: socialId,
                user_display: userDisplay,
                user_identifier: userIdentifier,
                user_message: userMessage
            },
            function (response)
            {
                console.log(response.btc_addr);
                $('#formBox').html(
                        "<hr><div><center><font size=\"5\">Waiting for payment</font></center></div><div class=\"spinner\"><div class=\"bounce1\"></div><div class=\"bounce2\"></div><div class=\"bounce3\"></div></div></br><p font-size=\"1\"><strong>Please note that the payment will only be tracked while this page is open, and you have a five minute time limit. If either the page gets closed, or five minutes elapses after you see the Bitcoin Cash address, please refresh the page to make a new payment request.</strong></p>"
                      )

		var toCashAddress = bchaddr.toCashAddress;
		const cashaddr_str = toCashAddress(response.btc_addr);

                $('#addressText').html(
                        "<p class=\"card-text\" style=\"font-size:12px;\">Please send BCH to: <span class=\"highlight\">" + cashaddr_str + "</span></p>" +
                        "<p class=\"card-text\" style=\"font-size:12px;\">You can use the QR code below as well.</p><hr>"
                        );
                $('#addressQR').html("");
                $('#addressQR').qrcode({
                    text : cashaddr_str,
                    render : "table"
                });
                $('#showModalButton').prop('disabled',true).html('Done...');
                $('#showModalButton').hide();
                $('#showSLPButton').hide();
                $('#tip-again').show();
                $('#back-btn').show();

                // We use a global variable for isPaid because it will be easier to 'clear' it later
                isPaid = setTimeout(function() {
                    verifyPayment(response.btc_addr)
                }, 2500);
            }
    , "json")
        .fail(
                function (request, status, errorThrown)
                {
                    $('#formBox').html(
                          "<p>Something went wrong, please try again.</p>"
                          )
                    // TODO: Handle Errors
                    console.log('We got an error! ' + status);
                }
             );

    // Proof of concept of live-updating code on page
    //<p><a href="bitcoin:{{ btc_addr }}" type="button" class="btn btn-primary">Launch Bitcoin Wallet</a>
    return false;
}

function createPayRequestSLP(userDisplay, userIdentifier, userMessage, socialId){
    // Get the value of some things on our form
    //$('#myModal').modal('show');
    // Create a new request to our server
    console.log("Social ID: " + socialId);
    console.log("User ID: " + userIdentifier);
    console.log("User Msg: " + userMessage);
    console.log("User Name: " + userDisplay);



    var resp = $.post('/_create_payreq',
            // This will be formatted as a 'body' string in the post request
            {
                social_id: socialId,
                user_display: userDisplay,
                user_identifier: userIdentifier,
                user_message: userMessage
            },
            function (response)
            {
                console.log(response.btc_addr);
                $('#formBox').html(
                        "<hr><div><center><font size=\"5\">Waiting for payment</font></center></div><div class=\"spinner\"><div class=\"bounce1\"></div><div class=\"bounce2\"></div><div class=\"bounce3\"></div></div></br><p font-size=\"1\"><strong>Please note that the payment will only be tracked while this page is open, and you have a five minute time limit. If either the page gets closed, or five minutes elapses after you see the Bitcoin Cash address, please refresh the page to make a new payment request.</strong></p>"
                      )

		var serverArray = ['https://rest.imaginary.cash/v2/slp/convert/', 'https://rest.bitcoin.com/v2/slp/convert/'];
		var randomServer = Math.floor(Math.random()*serverArray.length);
		$.getJSON(serverArray[randomServer]+response.btc_addr, function(data) {
			$('#addressText').html(
                        "<p class=\"card-text\" style=\"font-size:12px;\">Please send SPICE to: <span class=\"highlight\">" + data["slpAddress"] + "</span></p>" +
                        "<p class=\"card-text\" style=\"font-size:12px;\">You can use the QR code below as well.</p><hr>"
                        );
                $('#addressQR').html("");
                $('#addressQR').qrcode({
                    text : data["slpAddress"],
                    render : "table"
                });
		});

                $('#showSLPButton').prop('disabled',true).html('Done...');
                $('#showSLPButton').hide();
                $('#showModalButton').hide();
                $('#tip-again').show();
                $('#back-btn').show();

                // We use a global variable for isPaid because it will be easier to 'clear' it later
                isPaid = setTimeout(function() {
                    verifyPayment(response.btc_addr)
                }, 2500);
            }
    , "json")
        .fail(
                function (request, status, errorThrown)
                {
                    $('#formBox').html(
                          "<p>Something went wrong, please try again.</p>"
                          )
                    // TODO: Handle Errors
                    console.log('We got an error! ' + status);
                }
             );

    // Proof of concept of live-updating code on page
    //<p><a href="bitcoin:{{ btc_addr }}" type="button" class="btn btn-primary">Launch Bitcoin Wallet</a>
    return false;
}

function verifyPayment(btc_addr){
    // Does this work? I have no idea!
    var postVars = "btc_addr="+btc_addr+"&social_id="+socialId;

    var resp = $.post('/_verify_payment',
            {
                social_id: socialId,
                btc_addr: btc_addr,
                userID: $('#user_identifier').val(),
                userMsg: $('#user_message').val(),
                userName: $('#user_display').val()
            },
            function (response)
            {
                // Debug
                console.log(response.payment_verified)

                    // Unsure as to what it returns on the py
                    // You can make the json a boolean though?


                    if (response.payment_verified == "TRUE"){
                        // Clear our timeout
                        clearTimeout(isPaid);
                        $('#addressLocation').html(
                                "<strong>Payment Verified!</strong> <span class=\"highlight\">" + response.user_display + "</span> thanks you very much for the tip! Check the transaction with tx_hash:<div class=\"trunc\"><strong><a href=\"https://explorer.bitcoin.com/bch/tx/" + response.transaction_found + "\">" + response.transaction_found + "</a></strong></div>your donation has also been recorded in <strong><a href=\"/history\" >history</a></strong>" +
                                "<hr>" +
                                "<p>tipbitcoin.cash is a service provided for free and without ads, if you would like to help support " +
                                "the developer in general or help cover operating costs for tipbitcoin.cash, please consider also sending some support to the developer: </p>" +
                                "<p><a href=\"https://explorer.bitcoin.com/bch/address/bitcoincash:qq59s00zzjyn6d7s4flsg0w2qpnqdu3ck5nlwe6uem\"class=\"button1\" role=\"button\">Donate to tipbitcoin.cash!</a></p>"
                                );
                    }
                    else {
                        // Not Paid
                        isPaid = setTimeout(function() {
                            verifyPayment(btc_addr)
                        }, 2500);
                    }
            }
    , "json")
        .fail(
                function (request, status, errorThrown)
                {
                    // TODO: Handle Errors
                    console.log('We got an error! ' + status);
		    clearTimeout(isPaid);
		    isPaid = setTimeout(function() {
                            verifyPayment(btc_addr)
                        }, 2500);
                }
             );
}

function sendTestAlert(socialIdStr){
    // Does this work? I have no idea!
    var postVars = "social_id="+socialIdStr;

    var resp = $.post('/_test_alert',
            {
                social_id: socialIdStr
            },
            function (response)
            {
		console.log(response);
            }
    , "json")
        .fail(
                function (request, status, errorThrown)
                {
                    // TODO: Handle Errors
                    console.log('We got an error! ' + status);
                }
             );
}

function sendTestAlertSLP(socialIdStr){
    // Does this work? I have no idea!
    var postVars = "social_id="+socialIdStr;

    var resp = $.post('/_test_alert_slp',
            {
                social_id: socialIdStr
            },
            function (response)
            {
                console.log(response);
            }
    , "json")
        .fail(
                function (request, status, errorThrown)
                {
                    // TODO: Handle Errors
                    console.log('We got an error! ' + status);
                }
             );
}
