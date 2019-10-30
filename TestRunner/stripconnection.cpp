#include "stripconnection.hpp"
#include "ui_login.h"
#include "loginwindow.hpp"

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QThread>
#include <QtNetwork/QNetworkAccessManager>
#include <QtNetwork/QNetworkRequest>
#include <QtNetwork/QNetworkReply>

StripConnection::StripConnection(QObject * parent) :
    QObject(parent),
    manager(new QNetworkAccessManager(parent)),
    hostName(),
    port(80),
    loginInProgress(false),
    loggedIn(false),
    reply(nullptr)
{
}

StripConnection::~StripConnection()
{
    Q_ASSERT(manager != nullptr);

    if(loggedIn) {
        logout();
    }

    delete manager;
}

void StripConnection::post(const QString & path, const QByteArray & data)
{
    Q_ASSERT(manager != nullptr);
    if (commandRunning()) {
        return;
    }

    QUrl url(QString("https://%1:%2/%3").arg(hostName).arg(port).arg(path));

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    reply = manager->post(request, data);

    reply->connect(
        reply, &QNetworkReply::finished,
        reply, &QNetworkReply::deleteLater
    );

    reply->connect(
        reply, SIGNAL(finished()),
        this, SLOT(commandCompleted())
    );
}

void StripConnection::commandCompleted()
{
    bool errorCondition = false;

    if(reply->error() != QNetworkReply::NoError)
    {
        errorCondition = true;
        emit error(reply->errorString());
    }

    QByteArray rawAnswer(reply->readAll());

    QJsonDocument answer(QJsonDocument::fromJson(rawAnswer));
    if(answer.isObject())
    {
        QJsonObject answerObj(answer.object());
        if(!answerObj.contains("status")) {
            errorCondition = true;
            emit error(QString("Invalid JSON returned by the server: \"%1\""));
        }

        QString status{answerObj["status"].toString()};
        if(status.toUpper() != "OK")
        {
            QJsonDocument doc(answerObj);
            QString strJson(doc.toJson(QJsonDocument::Compact));
            errorCondition = true;
            emit error(QString("The server returned an error status: \"%1\"").arg(strJson));
        } else {
            emit success();
        }
    } else
    {
        errorCondition = true;
        emit error(QString("Invalid JSON returned by the server"));
    }

    if(loginInProgress && ! errorCondition) {
        loginInProgress = false;
        loggedIn = true;
    }

    reply = nullptr;
}

void StripConnection::login(
    const QString & aHostName,
    quint16 aPort,
    const QString & user,
    const QString & password
)
{
    Q_ASSERT(manager != nullptr);

    QString trueUser(user), truePassword(password);
    QUrl hostUrl;
    hostUrl.setHost(aHostName);
    hostUrl.setPort(aPort);

    if((trueUser.isEmpty() || hostUrl.host().isEmpty()) &&
            ! loadConfigurationFile(trueUser, truePassword)) {
        qDebug() << "Something was not provided, so I'm going to ask";

        // No user was provided and no configuration file has been found,
        // so we must prompt the user
        LoginWindow loginDialog;
        if (loginDialog.exec() == QDialog::Rejected)
            return;

        trueUser = loginDialog.userName();
        truePassword = loginDialog.password();

        hostUrl = QUrl::fromUserInput(loginDialog.host());
        hostName = hostUrl.host();
        port = static_cast<quint16>(hostUrl.port());
    }

    manager->connectToHost(hostUrl.url(), static_cast<quint16>(hostUrl.port()));

    QByteArray data = QString(R"json({"user": "%1", "password": "%2"})json")
            .arg(trueUser)
            .arg(truePassword)
            .toUtf8();
    post("rest/login", data);

    loginInProgress = true;
}

void StripConnection::logout()
{
    Q_ASSERT(manager != nullptr);

    QByteArray data = QString("{}").toUtf8();
    post("rest/logout", data);
}

void StripConnection::send(const QString & path, const QVariantMap & params)
{
    Q_ASSERT(manager != nullptr);

    QJsonDocument data(QJsonObject::fromVariantMap(params));
    post(path, data.toJson());
}

/* This function terminates in one of the following ways:
 *
 * 1. It reads the configuration file successfully and returns *true*:
 *    nothing else must be done, and the program can connect to the server;
 * 2. It does not find the configuration file and returns *false*:
 *    the program must ask the user about the connection details;
 * 3. It finds the configuration file, but it contains a syntax error:
 *    the function throws an exception, and the user should be notified
 *    immediately.
 */
bool StripConnection::loadConfigurationFile(QString & user, QString & password)
{
    const QString configFileName(QDir::homePath() + "/.strip/conf.json");
    QFile configFile(configFileName);

    qDebug() << "Trying to open the configuration file";

    if (! configFile.open(QFile::ReadOnly))
        return false;

    qDebug() << "Ok, I opened it, let's check what's inside.";

    QString fileBytes(configFile.readAll());
    QJsonParseError error;
    QJsonDocument confDoc = QJsonDocument::fromJson(fileBytes.toUtf8(), &error);
    if (error.error != QJsonParseError::NoError) {
        throw QString("Unable to load file \"%1\": %2")
                .arg(configFileName)
                .arg(error.errorString());
    }

    if (! confDoc.isObject()) {
        throw QString("Wrong data in file \"%1\"").arg(configFileName);
    }

    QJsonObject confObject = confDoc.object();
    if (confObject.contains("user")) {
        user = confObject["user"].toString();
    }
    if (confObject.contains("password")) {
        password = confObject["password"].toString();
    }
    if (confObject.contains("server")) {
        hostName = confObject["server"].toString();
    }
    if (confObject.contains("port")) {
        port = static_cast<quint16>(confObject["port"].toInt());
    }

    return true;
}
