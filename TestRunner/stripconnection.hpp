#pragma once

#include <QtNetwork/QNetworkAccessManager>
#include <QtNetwork/QNetworkReply>

class StripConnection : public QObject
{
private:
    Q_OBJECT

public:
    QNetworkAccessManager * manager;
    QString hostName;
    quint16 port;

    /* We need this variable because Qt network functions are asynchronous.
     * Once we send a "login" request to the server, we need to wait for the
     * server's answer before telling if the request was accepted or not. It is
     * really annoying, but this is life!
     */
    bool loginInProgress;
    bool loggedIn;
    QNetworkReply * reply;

    StripConnection(QObject * parent = nullptr);
    virtual ~StripConnection();

    bool commandRunning() const { return reply != nullptr; }

    void login(const QString & aHostName = QString(), quint16 aPort = 80,
        const QString & user = QString(),
        const QString & password = QString());
    void logout();
    void send(const QString & path, const QVariantMap & params);

private:
    void post(const QString & path, const QByteArray & data);
    bool loadConfigurationFile(QString & user, QString & password);

signals:
    // This signal is emitted whenever the server responds with an error
    void error(const QString & message);
    /* This signal is emitted if a request was successfully completed by the
     * server. */
    void success();

private slots:
    void commandCompleted();
};

