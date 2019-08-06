#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QCheckBox>
#include <QDebug>
#include <QFile>
#include <QFileDialog>
#include <QInputDialog>
#include <QMessageBox>
#include <QThread>
#include <QVariantMap>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow),
    commandList(new CommandList(this)),
    commandTimer(new QTimer(this)),
    delay_msec(250),
    connection(new StripConnection(this)),
    currentCommandIdx(-1)
{
    ui->setupUi(this);
    ui->commandView->setModel(commandList);

    setupConnection();

    logMessage("Ready");
}

MainWindow::~MainWindow()
{
    delete commandList;
    delete commandTimer;
    delete ui;
}

void MainWindow::setupConnection()
{
    connect(
        commandTimer, &QTimer::timeout,
        this, QOverload<>::of(&MainWindow::on_command_timer_triggered)
    );

    connect(
        connection, SIGNAL(error(const QString &)),
        this, SLOT(on_connection_error(const QString &))
    );

    connect(
        connection, SIGNAL(success()),
        this, SLOT(on_command_success())
    );
}

void MainWindow::loadJsonFile(const QString & fileName)
{
    QFile inputFile(fileName);
    if (! inputFile.open(QFile::ReadOnly)) {
        throw QString("Unable to open file %1").arg(fileName);
    }

    QTextStream inp(&inputFile);
    QString fileContents = inp.readAll();
    commandList->loadFromJson(fileContents);
    emit commandList->layoutChanged();
    ui->commandView->resizeColumnsToContents();
}

void MainWindow::logMessage(const QString & msg)
{
    ui->logMessageBrowser->append(QString("[%1] %2")
                                  .arg(QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))
                                  .arg(msg));
}

void MainWindow::on_action_quit_triggered()
{
    close();
}

void MainWindow::on_action_load_triggered()
{
    auto fileName = QFileDialog::getOpenFileName(
                this,
                tr("Open command sequence"),
                "",
                tr("JSON file (*.json);; All files (*)")
    );
    if(fileName.isEmpty())
        return;

    try {
        loadJsonFile(fileName);
        logMessage(QString("File \"%1\" loaded successfully").arg(fileName));

        updateProgressBar();
    }
    catch (const QString &errMsg) {
        QMessageBox::critical(
                    this,
                    QString("Error opening file \"%1\"").arg(fileName),
                    errMsg
        );
    }
}

void MainWindow::on_command_timer_triggered()
{
    Q_ASSERT(connection != nullptr);

    // If we're still waiting for an answer from the server, stop immediately
    if(currentCommandIdx != -1)
        return;

    if (! connection->loggedIn) {
        try {
            connection->login();
            logMessage("Login request to the server");

            int retryCount{5};
            while (connection->commandRunning() && retryCount > 0) {
                QThread::msleep(100);
                --retryCount;
            }

            if(! connection->commandRunning()) {
                throw QString("Unable to get a login token from the server");
            } else {
                logMessage("Connection to the server has been established, good!");
            }
        }
        catch (const QString & errMsg) {
            QString msg = QString("Error connecting to the server: %1").arg(errMsg);
            logMessage(msg);
            QMessageBox::critical(this, "Error connecting to the server", errMsg);
            commandTimer->stop();
            return;
        }
    }

    int curIdx{0};
    QDateTime now = QDateTime::currentDateTime();

    // Look for the first command that has not been executed yet
    for (auto & curCommand : commandList->command_list) {
        if (curCommand.type == CommandType::Wait) {
            qint64 waittime = curCommand.parameters["wait_time_s"].toInt();

            if (curCommand.time.isNull()) {
                // This wait command has not been started yet
                curCommand.time = now;
                logMessage(QString("Waiting for %1 s").arg(waittime));

                // Nothing else to do for the moment
                return;
            }

            // This wait has already started, let's check if it is done
            qint64 seconds = curCommand.time.secsTo(now);
            if (seconds < waittime) {
                // We still have to wait, so nothing else to do
                return;
            }
        } else {
            // Do this if the command is not a "wait"
            if (curCommand.time.isNull()) {
                currentCommandIdx = curIdx;
                // This is the first command whose date has not been set yet: run it!
                logMessage(QString("Running command: %1")
                           .arg(commandToStr(curCommand)));

                if (! ui->dryRunCheckBox->isChecked() &&
                        curCommand.type != CommandType::Wait) {
                    connection->send(curCommand.path, curCommand.parameters);
                } else {
                    on_command_success();
                }

                return;
            }
        }

        ++curIdx;
    }

    // If we reached this point, no other command must be executed
    logMessage("Script completed");
    stopTimer();
}

void MainWindow::on_command_success()
{
    if(currentCommandIdx != -1) {
        commandList->setCommandTime(currentCommandIdx, QDateTime::currentDateTime());
        currentCommandIdx = -1;

        updateProgressBar();
    }
}

void MainWindow::on_connection_error(const QString & msg)
{
    logMessage(msg);
}

void MainWindow::startTimer()
{
    ui->runNextButton->setEnabled(false);
    ui->addLogMessageButton->setEnabled(false);
    ui->runButton->setText(tr("&Stop"));

    commandTimer->start(delay_msec);
}

void MainWindow::stopTimer()
{
    commandTimer->stop();

    ui->runButton->setText(tr("&Run"));

    ui->runNextButton->setEnabled(true);
    ui->addLogMessageButton->setEnabled(true);
}

void MainWindow::on_runButton_clicked()
{
    if (commandTimer->isActive()) {
        stopTimer();
        logMessage("Command sequence paused");
    } else {
        startTimer();
        logMessage("Command sequence (re)started");
    }
}

void MainWindow::on_runNextButton_clicked()
{
    emit on_command_timer_triggered();
}

void MainWindow::updateProgressBar()
{
    ui->progressBar->setRange(0, commandList->command_list.length());

    int numOfCompletedCommands{0};
    for (auto & curCommand : commandList->command_list) {
        if (! curCommand.time.isNull()) {
            ++numOfCompletedCommands;
        }
    }
    ui->progressBar->setValue(numOfCompletedCommands);
}

void MainWindow::on_action_set_delay_triggered()
{
    bool ok;
    int newValue = QInputDialog::getInt(
        this,
        "Delay between commands",
        "Enter the delay (in msec)",
        250,
        50,
        5000,
        50,
        &ok
    );

    if(ok) {
        this->delay_msec = newValue;
    }
}

void MainWindow::on_addLogMessageButton_clicked()
{
    Q_ASSERT(connection != nullptr);

    // If we're still waiting for an answer from the server, stop immediately
    if(currentCommandIdx != -1) {
        logMessage("Failed to send log message, still waiting for the server "
                   "to acknowledge an old command");
        return;
    }

    QString message(ui->logMessageEdit->text());

    QVariantMap logMessageData;
    logMessageData["level"] = QString("INFO");
    logMessageData["message"] = message;
    connection->send("/rest/log", logMessageData);
    logMessage(QString("Log message sent to server: %1")
               .arg(message));
}

void MainWindow::on_action_reset_connection_triggered()
{
    if(connection != nullptr) {
        delete connection;
        connection = new StripConnection(this);
        setupConnection();
    }

    if(commandList != nullptr) {
        commandList->resetTimes();
        updateProgressBar();
    }

    currentCommandIdx = -1;
}
